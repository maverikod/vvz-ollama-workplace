"""
Model workspace client package: network interaction with model workspace server.

Config generator and validator for client adapter config.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from model_workspace_client.config_validator import (
    ModelWorkspaceClientConfigError,
    validate_config,
    validate_config_dict,
)

__all__ = [
    "ModelWorkspaceClientConfigError",
    "validate_config",
    "validate_config_dict",
]
