"""Jerarquía de excepciones unificada para asyncio-manager.

Cubre tanto errores del protocolo AMI como del protocolo AGI.
Todas las excepciones heredan de AsyncioManagerError.
"""


class AsyncioManagerError(Exception):
    """Excepción base para toda la librería asyncio-manager.

    Todas las excepciones personalizadas heredan de esta clase,
    permitiendo capturar cualquier error de la librería con::

        try:
            await manager.connect()
        except AsyncioManagerError as e:
            logger.error(f"Error en asyncio-manager: {e}")
    """
    pass


class ConnectionError(AsyncioManagerError):
    """Error al establecer o mantener la conexión con Asterisk.

    Se lanza cuando:
    - El servidor Asterisk no está accesible (host:puerto incorrecto).
    - La conexión se pierde inesperadamente.
    - El servidor rechaza la conexión.
    """
    pass


class AuthenticationError(AsyncioManagerError):
    """Error de autenticación en el AMI.

    Se lanza cuando:
    - El username o secret proporcionados son incorrectos.
    - El usuario no tiene permisos para la acción solicitada.
    - El servidor rechaza el challenge MD5.
    """
    pass


class TimeoutError(AsyncioManagerError):
    """La operación excedió el tiempo máximo de espera.

    Se lanza cuando:
    - Una acción AMI no recibe respuesta dentro del timeout.
    - La conexión no se establece dentro del connect_timeout.
    - La lectura de un mensaje supera el read_timeout.
    """
    pass


class ProtocolError(AsyncioManagerError):
    """Error en el protocolo AMI.

    Se lanza cuando:
    - Se recibe un mensaje mal formado desde Asterisk.
    - El parsing del mensaje falla.
    - Se detecta un mensaje incompleto o corrupto.
    """
    pass


class DisconnectedError(AsyncioManagerError):
    """El Manager no está conectado a Asterisk.

    Se lanza cuando se intenta enviar una acción
    sin tener una conexión activa con el servidor.
    """
    pass


class ActionError(AsyncioManagerError):
    """La acción AMI fue rechazada por Asterisk.

    Se lanza cuando:
    - Asterisk responde con 'Response: Error'.
    - La acción no es válida para el contexto actual.
    - Faltan parámetros requeridos en la acción.
    """
    pass


class AGIError(AsyncioManagerError):
    """Error base para el protocolo AGI.

    Todos los errores específicos de AGI heredan de esta clase.
    """

    def __init__(self, message: str, items: dict | None = None) -> None:
        """Inicializa el error AGI.

        Args:
            message: Mensaje descriptivo del error.
            items: Diccionario opcional con parámetros adicionales del error.
        """
        super().__init__(message)
        self.items = items or {}


class AGIResultHangup(AGIError):
    """La llamada fue colgada durante la ejecución del comando AGI."""
    pass


class AGINoResultError(AGIError):
    """El comando AGI no retornó ningún resultado."""
    pass


class AGIUnknownError(AGIError):
    """Error desconocido en la respuesta del comando AGI."""
    pass


class AGIAppError(AGIError):
    """La aplicación AGI retornó un error."""
    pass


class AGIDeadChannelError(AGIError):
    """El canal está muerto y no se puede ejecutar el comando AGI."""
    pass


class AGIInvalidCommand(AGIError):
    """El comando AGI enviado no es válido."""
    pass


class AGIUsageError(AGIError):
    """Uso incorrecto del comando AGI (parámetros inválidos)."""
    pass
