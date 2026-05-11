import logging

from datamind.interfaces.observability import ObservabilityInterface


class StdoutObservability(ObservabilityInterface):
    def __init__(self):
        self._logger = logging.getLogger("datamind")

    def log(self, level: str, message: str, context: dict | None = None) -> None:
        log_method = getattr(self._logger, level.lower(), self._logger.info)
        if context:
            log_method(f"{message} | context={context}")
        else:
            log_method(message)

    def metric(self, name: str, value: float, tags: dict | None = None) -> None:
        pass

    def trace(self, span_name: str, parent_id: str | None = None) -> str:
        return span_name

    def alert(self, severity: str, title: str, detail: str) -> None:
        self._logger.warning(f"[ALERT:{severity}] {title}: {detail}")
