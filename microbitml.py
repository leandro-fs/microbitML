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
                error_handler(halt=False, error_code=9, description=status_description)
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