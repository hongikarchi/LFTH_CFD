from enum import StrEnum


class SchemaVersion(StrEnum):
    """params.json / metrics.json schema versions.

    Add new versions here as the schema evolves. Keep old versions defined
    until all `runs/` candidates have been migrated.
    """

    V1_0 = "1.0"


CURRENT_PARAMS_VERSION = SchemaVersion.V1_0
CURRENT_METRICS_VERSION = SchemaVersion.V1_0
