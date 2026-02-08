from typing import Type, TypeVar

from pydantic import BaseModel
from workflows.resource import ResourceConfig


ModelT = TypeVar("ModelT", bound=BaseModel)


def load_config_from_json(
    *,
    model: Type[ModelT],
    config_file: str,
    path_selector: str | None = None,
    label: str | None = None,
    description: str | None = None,
) -> ModelT:
    """Load a pydantic model from a JSON config file using Workflows ResourceConfig."""

    descriptor = ResourceConfig(
        config_file=config_file,
        path_selector=path_selector,
        label=label,
        description=description,
    )
    descriptor.set_type_annotation(model)
    return descriptor.call()
