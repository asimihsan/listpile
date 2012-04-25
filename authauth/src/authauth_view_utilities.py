import os
import sys
import uuid
import logging
import re
import base64

def normalize_uuid_string(uuid_string):    
    #logging.debug("entry. uuid_string: %s" % (uuid_string, ))
    try:
        uuid_obj = uuid.UUID(uuid_string)
    except:
        return_value = uuid_string
    else:
        return_value = uuid_obj.hex
    #logging.debug("returning: %s" % (return_value, ))
    return return_value    

REGEXP_BASE64 = re.compile("^[A-Za-z0-9-_=]+$")
def validate_base64_parameter(parameter, is_uuid=True):
    """ Given a string in variable 'parameter' confirm that it is a
    URL safe base64 encoded string. If is_uuid is True then also
    check that the base64 string decodes to the bytes of a UUID. If
    is_uuid is False do not perform the UUID check.
    
    Returns False is not valid, else returns True."""    
    logger = logging.getLogger("validate_base64_parameter")
    logger.debug("entry. parameter: %s, is_uuid: %s" % (parameter, is_uuid))
    
    match = REGEXP_BASE64.search(parameter)    
    if not match:
        logger.debug("regexp didn't match.")
        return False    
    try:
        decoded = base64.urlsafe_b64decode(parameter)
        if is_uuid:
            uuid_obj = uuid.UUID(bytes=decoded)
    except:
        logger.exception("unhandled exception")
        return False
    else:
        logger.debug("valid parameter")
        return True
        
def validate_uuid_string(parameter):
    """ Given a string corresponding to the ASCII version of
    the UUID (i.e. not the bytes) confirm it is a valid UUID."""
    try:
        uuid_obj = uuid.UUID(parameter)
    except:
        return False
    else:
        return True
        
def convert_uuid_string_to_base64(uuid_string):
    return base64.urlsafe_b64encode(uuid.UUID(uuid_string).bytes)    

def convert_base64_to_uuid_string(base64_string):
    logger = logging.getLogger("List.convert_base64_to_uuid_string")        
    decoded = base64.urlsafe_b64decode(base64_string)        
    return uuid.UUID(bytes=decoded).hex