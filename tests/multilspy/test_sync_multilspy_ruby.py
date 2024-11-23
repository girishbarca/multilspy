"""
This file contains tests for running the Ruby Language Server: ruby-lsp
"""

import time
from multilspy.language_server import SyncLanguageServer
from multilspy.multilspy_config import Language
from tests.test_utils import create_test_context
from pathlib import PurePath

def test_multilspy_ruby_todo():
    """
    Test the working of multilspy with javascript repository - todo
    """
    code_language = Language.RUBY
    params = {
        "code_language": code_language,
        "repo_url": "https://github.com/naoty/todo/",
        "repo_commit": "0e589ebe2a70b5d9e777d86a5a6ca1a5a491106d"
    }
    with create_test_context(params) as context:
        lsp = SyncLanguageServer.create(
            context.config, context.logger, context.source_directory)
        # All the communication with the language server must be performed inside the context manager
        # The server process is started when the context manager is entered and is terminated when the context manager is exited.
        # The context manager is an asynchronous context manager, so it must be used with async with.
        with lsp.start_server():
            path = str(PurePath("lib/todo/commands/printable.rb"))
            result = lsp.request_references(path, 5, 7)
            assert isinstance(result, list)
            assert len(result) == 11

            for item in result:
                del item["uri"]
                del item["absolutePath"]

            assert result == [
                {
                    "relativePath": str(PurePath("lib/todo/commands/add.rb")),
                    "range": {
                        "start": {"line": 32, "character": 4},
                        "end": {"line": 32, "character": 15},
                    },
                },
                {
                    "relativePath": str(PurePath("lib/todo/commands/archive.rb")),
                    "range": {
                        "start": {"line": 19, "character": 4},
                        "end": {"line": 19, "character": 15},
                    },
                },
                {
                    "relativePath": str(PurePath("lib/todo/commands/delete.rb")),
                    "range": {
                        "start": {"line": 26, "character": 4},
                        "end": {"line": 26, "character": 15},
                    },
                },
                {
                    "relativePath": str(PurePath("lib/todo/commands/list.rb")),
                    "range": {
                        "start": {"line": 17, "character": 4},
                        "end": {"line": 17, "character": 15},
                    },
                },
                {
                    "relativePath": str(PurePath("lib/todo/commands/move.rb")),
                    "range": {
                        "start": {"line": 45, "character": 4},
                        "end": {"line": 45, "character": 15},
                    },
                },
                {
                    "relativePath": str(PurePath("lib/todo/commands/update.rb")),
                    "range": {
                        "start": {"line": 23, "character": 4},
                        "end": {"line": 23, "character": 15},
                    },
                },
                {
                    "relativePath": str(PurePath("spec/todo/commands/printable_spec.rb")),
                    "range": {
                        "start": {"line": 27, "character": 16},
                        "end": {"line": 27, "character": 27},
                    },
                },
                {
                    "relativePath": str(PurePath("spec/todo/commands/printable_spec.rb")),
                    "range": {
                        "start": {"line": 48, "character": 16},
                        "end": {"line": 48, "character": 27},
                    },
                },
                {
                    "relativePath": str(PurePath("spec/todo/commands/printable_spec.rb")),
                    "range": {
                        "start": {"line": 67, "character": 16},
                        "end": {"line": 67, "character": 27},
                    },
                },
                {
                    "relativePath": str(PurePath("lib/todo/commands/printable.rb")),
                    "range": {
                        "start": {"line": 5, "character": 6},
                        "end": {"line": 5, "character": 17},
                    },
                },
                {
                    "relativePath": str(PurePath("lib/todo/commands/printable.rb")),
                    "range": {
                        "start": {"line": 11, "character": 6},
                        "end": {"line": 11, "character": 17},
                    },
                },
            ]

            path = str(PurePath("lib/todo/commands/add.rb"))
            result = lsp.request_definition(path, 32, 10)
            if len(result) == 0:
                # No reliable way to check if ruby lsp has finished indexing yet.
                time.sleep(1)
                result = lsp.request_definition(path, 32, 10)
            assert isinstance(result, list)
            assert len(result) == 1

            item = result[0]
            del item["uri"]
            del item["absolutePath"]
            assert item["relativePath"] == str(
                PurePath("lib/todo/commands/printable.rb"))
            assert item["range"] == {
                "start": {"line": 5, "character": 6},
                "end": {"line": 5, "character": 17},
            }

            path = str(PurePath("spec/todo/file_repository_spec.rb"))
            result = lsp.request_definition(path, 26, 20)
            assert isinstance(result, list)
            assert len(result) == 1
            item = result[0]
            assert item["relativePath"] == str(
                PurePath("lib/todo/file_repository.rb"))
            assert item["range"] == {
                "start": {"line": 5, "character": 6},
                "end": {"line": 5, "character": 26},
            }
