# microbitml.py - Protocolo simple de comunicacion radio para micro:bit

__all__ = ["RadioProtocol"]

class RadioProtocol:
    """
    Protocolo basico para comunicacion entre microbits
    Sin dependencias externas para evitar imports circulares
    """
    
    def __init__(self, device_id=None):
        """
        Inicializa el protocolo
        device_id: ID opcional del dispositivo (para estudiantes)
        """
        self.device_id = device_id
        self.registered = False
    
    # === COMANDOS BROADCAST ===
    
    @staticmethod
    def crear_report():
        """Crea mensaje REPORT para descubrimiento"""
        return "REPORT"
    
    @staticmethod
    def crear_question(question_data):
        """Crea mensaje QUESTION con datos de pregunta"""
        return f"QUESTION:{question_data}"
    
    @staticmethod
    def crear_ping(device_id):
        """Crea mensaje PING para dispositivo especifico"""
        return f"PING:{device_id}"
    
    # === RESPUESTAS INDIVIDUALES ===
    
    def crear_id_response(self):
        """Crea respuesta ID con device_id propio"""
        if not self.device_id:
            raise ValueError("device_id no configurado")
        return f"ID:{self.device_id}"
    
    @staticmethod
    def crear_ack(device_id):
        """Crea ACK para device_id especifico"""
        return f"ACK:{device_id}"
    
    @staticmethod
    def crear_pong(device_id):
        """Crea respuesta PONG"""
        return f"PONG:{device_id}"
    
    def crear_answer(self, opciones):
        """
        Crea respuesta con opciones guardadas
        opciones: lista de strings, ej: ['A', 'B', 'C']
        """
        if not self.device_id:
            raise ValueError("device_id no configurado")
        opciones_str = ','.join(opciones)
        return f"ANSWER:{self.device_id}:{opciones_str}"
    
    # === DECODIFICACION ===
    
    @staticmethod
    def decodificar(mensaje):
        """
        Decodifica mensaje recibido
        Retorna: (tipo, datos)
        Tipos: REPORT, QUESTION, PING, ID, ACK, PONG, ANSWER
        """
        if not mensaje:
            return (None, None)
        
        # Mensajes sin payload
        if mensaje == "REPORT":
            return ("REPORT", None)
        
        # Mensajes con payload
        if ':' in mensaje:
            partes = mensaje.split(':', 1)
            tipo = partes[0]
            datos = partes[1] if len(partes) > 1 else None
            return (tipo, datos)
        
        return (None, None)
    
    @staticmethod
    def extraer_device_id(mensaje):
        """
        Extrae device_id de mensajes tipo ID:xxx, ACK:xxx, PING:xxx
        Retorna: device_id o None
        """
        tipo, datos = RadioProtocol.decodificar(mensaje)
        if tipo in ["ID", "ACK", "PING", "PONG"]:
            return datos
        return None
    
    @staticmethod
    def extraer_answer(mensaje):
        """
        Extrae respuesta de mensaje ANSWER:device_id:A,B,C
        Retorna: (device_id, [opciones]) o (None, None)
        """
        tipo, datos = RadioProtocol.decodificar(mensaje)
        if tipo == "ANSWER" and datos:
            partes = datos.split(':', 1)
            if len(partes) == 2:
                device_id = partes[0]
                opciones = partes[1].split(',')
                return (device_id, opciones)
        return (None, None)
    
    # === VALIDACION ===
    
    def validar_ack(self, mensaje):
        """Verifica si el ACK es para este dispositivo"""
        device_id = self.extraer_device_id(mensaje)
        return device_id == self.device_id
    
    def validar_ping(self, mensaje):
        """Verifica si el PING es para este dispositivo"""
        device_id = self.extraer_device_id(mensaje)
        return device_id == self.device_id
    
    # === ESTADO ===
    
    def marcar_registrado(self):
        """Marca dispositivo como registrado"""
        self.registered = True
    
    def resetear_registro(self):
        """Resetea estado de registro"""
        self.registered = False
    
    def esta_registrado(self):
        """Retorna si el dispositivo esta registrado"""
        return self.registered


# === FUNCIONES DE UTILIDAD ===

def test_protocol():
    """Test basico del protocolo"""
    print("=== Test RadioProtocol ===")
    
    # Crear protocolo
    proto = RadioProtocol(device_id="aabbccdd")
    
    # Test mensajes broadcast
    assert proto.crear_report() == "REPORT"
    assert proto.crear_ping("1234") == "PING:1234"
    
    # Test respuestas
    assert proto.crear_id_response() == "ID:aabbccdd"
    assert proto.crear_ack("1234") == "ACK:1234"
    assert proto.crear_answer(['A', 'C']) == "ANSWER:aabbccdd:A,C"
    
    # Test decodificacion
    assert proto.decodificar("REPORT") == ("REPORT", None)
    assert proto.decodificar("ID:1234") == ("ID", "1234")
    assert proto.decodificar("ACK:aabbccdd") == ("ACK", "aabbccdd")
    
    # Test extraccion
    assert proto.extraer_device_id("ID:1234") == "1234"
    assert proto.extraer_answer("ANSWER:dev1:A,B") == ("dev1", ["A", "B"])
    
    # Test validacion
    assert proto.validar_ack("ACK:aabbccdd") == True
    assert proto.validar_ack("ACK:1234") == False
    
    print("Todos los tests pasaron!")


if __name__ == "__main__":
    test_protocol()
# microbitml.py - Radio communication module
__all__ = ["test_module_import", "RadioPacket"]

def test_module_import():
    print("microbitml module loaded successfully")

class RadioPacket():
    # Formato: version_token,message_bus,sender_role,payload
    
    def __init__(self):
        self.fixed_role = None  # Rol fijo, si se asigna
        self.fixed_bus = None   # Bus fijo, si se asigna
    
    def encode(self, payload):
        from main import version_token, message_bus, current_role
        
        # CORRECCION: Usar valores fijos si existen, sino usar globals
        sender_role = self.fixed_role if self.fixed_role else current_role
        sender_bus = self.fixed_bus if self.fixed_bus is not None else message_bus
        
        encoded_message = version_token + ","
        encoded_message += "{},".format(sender_bus)
        encoded_message += "{},".format(sender_role)
        encoded_message += str(payload).replace(",", "_coma_")
        
        return encoded_message
    
    def decode(self, received_message, valid_origin_roles):
        from main import version_token, message_bus, current_role, error_handler
        
        is_valid = False
        status_description = ""
        sender_role = ""
        decoded_payload = ""
        
        # CORRECCION: Usar bus fijo si existe
        expected_bus = self.fixed_bus if self.fixed_bus is not None else message_bus
        
        message_parts = received_message.split(",")
        
        try:
            # Validar version
            received_version = message_parts[0]
            if received_version != version_token:
                status_description = "parts[version_token]={}, expected:{}".format(
                    received_version, version_token
                )
                #error_handler(halt=False, error_code=9, description=status_description)
                print("DEBUG: packet ignored, {}".format(status_description))
                raise ValueError
            
            # Validar bus
            received_bus = message_parts[1]
            if received_bus != str(expected_bus):
                status_description = "parts[message_bus]:{}, expected:{}".format(
                    received_bus, str(expected_bus)
                )
                raise ValueError
            
            # Validar rol origen
            received_role = message_parts[2]
            
            # Verificar si rol esta en roles validos
            if received_role in valid_origin_roles:
                sender_role = received_role
            else:
                status_description = "parts[originRoles]: {} not in '{}'".format(
                    received_role, str(valid_origin_roles)
                )
                # Detectar clonacion de roles (mismo rol, diferente dispositivo)
                # NOTA: Con el filtro en on_message_received(), esto solo detecta
                # clonacion REAL si dos dispositivos distintos tienen el mismo rol
                if received_role == current_role:
                    error_handler(
                        halt=True, 
                        error_code=1, 
                        description="Role cloning detected: {}".format(current_role)
                    )
                raise ValueError
            
            # Descodificar payload
            raw_payload = message_parts[3]
            decoded_payload = raw_payload.replace("_coma_", ",")
            
            is_valid = True
            status_description = "OK"
            
        except Exception as e:
            print("DEBUG:RadioPacket.decode:exception={},desc={},received_message='{}'".format(
                e, status_description, received_message
            ))
        
        return is_valid, status_description, sender_role, decoded_payload
