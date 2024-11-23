"""
Provides Ruby specific instantiation of the LanguageServer class. Contains various configurations and settings specific to Ruby.
"""

import asyncio
import json
import shutil
import logging
import os
import pwd
import subprocess
import pathlib
from contextlib import asynccontextmanager
from typing import AsyncIterator

from multilspy.multilspy_logger import MultilspyLogger
from multilspy.language_server import LanguageServer
from multilspy.lsp_protocol_handler.server import ProcessLaunchInfo
from multilspy.lsp_protocol_handler.lsp_types import InitializeParams
from multilspy.multilspy_config import MultilspyConfig
from multilspy.multilspy_utils import PlatformUtils, PlatformId


class RubyLSP(LanguageServer):
    """
    Provides Ruby specific instantiation of the LanguageServer class. Contains various configurations and settings specific to Ruby.
    """

    def __init__(self, config: MultilspyConfig, logger: MultilspyLogger, repository_root_path: str):
        """
        Creates a RubyLSP instance. This class is not meant to be instantiated directly. Use LanguageServer.create() instead.
        """
        self.ruby_ls_dir = os.path.join(
            os.path.dirname(__file__), "static", "ruby-lsp")
        ruby_lsp_command = self.setup_runtime_dependencies(
            logger, config)
        super().__init__(
            config,
            logger,
            repository_root_path,
            ProcessLaunchInfo(cmd=ruby_lsp_command,
                              cwd=self.ruby_ls_dir),
            "ruby",
        )
        self.server_ready = asyncio.Event()

    def setup_runtime_dependencies(self, logger: MultilspyLogger, config: MultilspyConfig) -> str:
        """
        Setup runtime dependencies for Ruby Language Server.
        """
        platform_id = PlatformUtils.get_platform_id()

        valid_platforms = [
            PlatformId.LINUX_x64,
            PlatformId.LINUX_arm64,
            PlatformId.OSX,
            PlatformId.OSX_x64,
            PlatformId.OSX_arm64,
            PlatformId.WIN_x64,
            PlatformId.WIN_arm64,
        ]
        assert platform_id in valid_platforms, f"Platform {
            platform_id} is not supported for multilspy ruby at the moment"

        with open(os.path.join(os.path.dirname(__file__), "runtime_dependencies.json"), "r") as f:
            d = json.load(f)
            del d["_description"]

        runtime_dependencies = d.get("runtimeDependencies", [])
        ruby_lsp_command = "bundle exec ruby-lsp"

        # Verify both node and npm are installed
        is_node_installed = shutil.which('bundle') is not None
        assert is_node_installed, "bundle is not installed or isn't in PATH. Please install bundle and try again."
        is_npm_installed = shutil.which('gem') is not None
        assert is_npm_installed, "gem is not installed or isn't in PATH. Please install gem and try again."

        # Install ruby-lsp gem as a non-root user
        if not os.path.exists(self.ruby_ls_dir):
            os.makedirs(self.ruby_ls_dir, exist_ok=True)
            for dependency in runtime_dependencies:
                user = pwd.getpwuid(os.getuid()).pw_name
                subprocess.run(
                    dependency["command"],
                    shell=True,
                    check=True,
                    user=user,
                    cwd=self.ruby_ls_dir,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
        return ruby_lsp_command

    def _get_initialize_params(self, repository_absolute_path: str) -> InitializeParams:
        """
        Returns the initialize params for the Ruby Language Server.
        """
        with open(os.path.join(os.path.dirname(__file__), "initialize_params.json"), "r") as f:
            d = json.load(f)

        del d["_description"]

        d["processId"] = os.getpid()
        assert d["rootPath"] == "$rootPath"
        d["rootPath"] = repository_absolute_path

        assert d["rootUri"] == "$rootUri"
        d["rootUri"] = pathlib.Path(repository_absolute_path).as_uri()

        assert d["workspaceFolders"][0]["uri"] == "$uri"
        d["workspaceFolders"][0]["uri"] = pathlib.Path(
            repository_absolute_path).as_uri()

        assert d["workspaceFolders"][0]["name"] == "$name"
        d["workspaceFolders"][0]["name"] = os.path.basename(
            repository_absolute_path)

        return d

    @asynccontextmanager
    async def start_server(self) -> AsyncIterator["RubyLSP"]:
        """
        Starts Ruby LSP, waits for the server to be ready and yields the LanguageServer instance.

        Usage:
        ```
        async with lsp.start_server():
            # LanguageServer has been initialized and ready to serve requests
            await lsp.request_definition(...)
            await lsp.request_references(...)
            # Shutdown the LanguageServer on exit from scope
        # LanguageServer has been shutdown
        """

        async def execute_client_command_handler(params):
            return []

        async def do_nothing(params):
            return

        async def window_log_message(msg):
            self.logger.log(f"LSP: window/logMessage: {msg}", logging.INFO)
            if "Finished" in msg["message"]:
                self.server_ready.set()

        self.server.on_notification("window/logMessage", window_log_message)
        self.server.on_request(
            "workspace/executeClientCommand", execute_client_command_handler)
        self.server.on_notification("$/progress", do_nothing)
        self.server.on_notification(
            "textDocument/publishDiagnostics", do_nothing)

        async with super().start_server():
            self.logger.log("Starting Ruby server process", logging.INFO)
            await self.server.start()
            initialize_params = self._get_initialize_params(
                self.repository_root_path)

            self.logger.log(
                "Sending initialize request from LSP client to LSP server and awaiting response",
                logging.INFO,
            )
            await self.server.send.initialize(initialize_params)

            self.server.notify.initialized({})
            self.completions_available.set()

            await self.server_ready.wait()
            yield self

            await self.server.shutdown()
            await self.server.stop()
