from cerberus import Validator
import json
import time


def referer_validator(referer_regex, value):
    if len(value) < 1 or len(value) > 256:
        return False
    return referer_regex.match(value)


class ValidationError(Exception):
    def __init__(self, errors):
        self.errors = errors
        super().__init__(self.format_validation_error(errors))
    
    def format_validation_error(self, errors):
        error_key = next(iter(errors))
        return f"Validation Error: {error_key.replace('_', ' ')} {errors[error_key][0]}"


def validate_json(json_obj, schema):
    v = Validator()
    # schema = {k: VALIDATORS[k] for (k, v) in json_obj.items()}
    if v.validate(json_obj, schema):
        return v.document
    else:
        raise ValidationError(v.errors)


def cerberus_tags(field, value, error):
    if isinstance(value, str) and value != '':
        try:
            _value = json.loads(value)
            if not isinstance(_value, list):
                return error(field, 'JSON must deserialize to a list')
            if len(_value) < 1 or len(_value) > 3:
                return error(field, 'must only contain 1-3 tags')
        except:
            return error(field, 'must be a JSON deserializable list of tags')
    elif not isinstance(value, str):
        return error(field, 'must be a string of a JSON serialized list of tags')


schemas = {
    'email_address': {
        'required': True,
        'type': 'string',
        'regex': '^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))'
    },
    'user_level': {
        'required': True,
        'type': 'integer',
        'min': 1,
        'max': 9
    },
    'first_name': {
        'required': True,
        'type': 'string',
        'regex': '^[A-Za-z]+$',
        'minlength': 1,
        'maxlength': 20
    },
    'last_name': {
        'required': True,
        'type': 'string',
        'regex': '^[A-Za-z]+$',
        'minlength': 1,
        'maxlength': 20
    },
    'mobile_number': {
        'required': False,
        'type': 'integer',
        'min': 1000000000,
        'max': 9999999999999
    },
    'auth_method': {
        'required': True,
        'type': 'string',
        'allowed': [
            'email_address',
            'mobile_number',
            'mobile_number_no'
        ]
    },
    'datatables_bound': {
        'required': True,
        'type': 'integer',
        'min': 0,
        'max': 9999999
    },
    'invite_code': {
        'required': True,
        'type': 'string',
        'minlength': 15,
        'maxlength': 52,
        'regex': '^[a-zA-Z0-9_]+( [a-zA-Z0-9_]+)*$'
    }
}

ADD_USER_SCHEMAS = (
    {}
)

REGISTRATION_VALIDATOR = {
    'email_address': schemas['email_address'],
    'mobile_number': {
        'required': True,
        'type': 'string',
        'regex': '^[+]*[(]{0,1}[0-9]{1,4}[)]{0,1}[-\s\./0-9]*$'
    },
    'first_name': schemas['first_name'],
    'last_name': schemas['last_name'],
    'invite_code': schemas['invite_code'],
    'password': {
        'required': True,
        'type': 'string',
        'regex': "^(?=.*[0-9])(?=.*[a-zA-Z])(?=\S+$).{6,20}$",
        'minlength': 8,
        'maxlength': 100
    }
}
ADD_USER_VALIDATOR = {
    'email_address': {
        'required': False,
        'type': 'string',
        'regex': '^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))'
    },
    'mobile_number': {
        'required': False,
        'type': 'string',
        'regex': '^[+]*[(]{0,1}[0-9]{1,4}[)]{0,1}[-\s\./0-9]*$'
    },
    'user_level': schemas['user_level'],
    'first_name': schemas['first_name'],
    'last_name': schemas['last_name']
}
ADD_USER_VALIDATOR_EMAIL = {
    'email_address': {
        'required': True,
        'type': 'string',
        'regex': '^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))'
    },
    'mobile_number': {
        'required': False,
        'type': 'string'
    },
    'user_level': schemas['user_level'],
    'first_name': schemas['first_name'],
    'last_name': schemas['last_name']
}
ADD_USER_VALIDATOR_PHONE = {
    'mobile_number': {
        'required': True,
        'type': 'string',
        'regex': '^[+]*[(]{0,1}[0-9]{1,4}[)]{0,1}[-\s\./0-9]*$'
    },
    'email_address': {
        'required': False,
        'type': 'string'
    },
    'user_level': schemas['user_level'],
    'first_name': schemas['first_name'],
    'last_name': schemas['last_name']
}
DATATABLES_VALIDATOR = {
    'start': {
        'required': False,
        'type': 'integer',
        'nullable': True,
        'min': 0,
        'max': 9999999
    },
    'len': {
        'required': False,
        'type': 'integer',
        'nullable': True,
        'min': 0,
        'max': 9999999
    },
    'end': {
        'required': False,
        'type': 'integer',
        'nullable': True,
        'min': 0,
        'max': 9999999
    }
}

INVENTORY_ITEM_VALIDATOR = {
    'item_name': {
        'required': True,
        'type': 'string',
        'regex': '^[a-zA-Z0-9_.-/&"#%]+( [a-zA-Z0-9_.-/&"#%]+)*$',
        'minlength': 3,
        'maxlength': 30
    },
    'item_description': {
        'required': False,
        'empty': True,
        'nullable': True,
        'default': 'No description.',
        'type': 'string',
        'regex': '^[a-zA-Z0-9_.-/&"#%-]+( [a-zA-Z0-9_.-/&"#%-]+)*$',
        'minlength': 0,
        'maxlength': 128
    },
    'tags': {
        'required': True,
        'check_with': cerberus_tags
    },
    'section': {
        'required': True,
        'type': 'integer',
        'coerce': int,
        'min': 1,
        'max': 9999
    },
    'location': {
        'required': True,
        'type': 'integer',
        'coerce': int,
        'min': 1,
        'max': 9999
    },
    'quant': {
        'required': True,
        'type': 'integer',
        'coerce': int,
        'min': 0,
        'max': 99999999
    },
    'internal_code': {
        'required': True,
        'type': 'string',
        'coerce': str,
        'minlength': 1
    },
    'part_code': {
        'required': False,
        'type': 'string',
        'coerce': str,
        'minlength': 1
    },
    'photo_ext': {
        'required': True,
        'type': 'string',
        'allowed': ['png', 'jpg', 'jpeg', 'undefined']
    },
    'distributor': {
        'required': True,
        'type': 'integer',
        'coerce': int,
        'min': 0,
        'max': 99999999
    },
    'alert_thresh': {
        'required': True,
        'type': 'integer',
        'coerce': int,
        'min': 1,
        'max': 99999999
    }
}

INVENTORY_EDIT_VALIDATOR = {
    'item_id': {
        'required': True,
        'type': 'integer',
        'coerce': int,
        'min': 1,
        'max': 99999
    },
    'item_name': {
        'required': True,
        'type': 'string',
        'regex': '^[a-zA-Z0-9_.-/&"#%]+( [a-zA-Z0-9_.-/&"#%]+)*$',
        'minlength': 3,
        'maxlength': 30
    },
    'item_description': {
        'required': False,
        'empty': True,
        'nullable': True,
        'default': 'No description.',
        'type': 'string',
        'regex': '^[a-zA-Z0-9_.-/&"#%-]+( [a-zA-Z0-9_.-/&"#%-]+)*$',
        'minlength': 0,
        'maxlength': 128
    },
    'section': {
        'required': True,
        'type': 'integer',
        'coerce': int,
        'min': 1,
        'max': 9999
    },
    'location': {
        'required': True,
        'type': 'integer',
        'coerce': int,
        'min': 1,
        'max': 9999
    },
    'quant': {
        'required': True,
        'type': 'integer',
        'coerce': int,
        'min': 0,
        'max': 99999999
    },
    'internal_code': {
        'required': True,
        'type': 'string',
        'coerce': str,
        'minlength': 1
    },
    'part_code': {
        'required': False,
        'type': 'string',
        'coerce': str,
        'minlength': 1
    },
    'photo_ext': {
        'required': True,
        'type': 'string',
        'allowed': ['png', 'jpg', 'jpeg', 'undefined']
    },
    'distributor': {
        'required': True,
        'type': 'integer',
        'coerce': int,
        'min': 0,
        'max': 99999999
    },
    'alert_thresh': {
        'required': True,
        'type': 'integer',
        'coerce': int,
        'min': 1,
        'max': 99999999
    }
}

ITEM_REQUEST_VALIDATOR = {
    'item_id': {
        'required': True,
        'type': 'integer',
        'coerce': int,
        'min': 1,
        'max': 99999
    }
}

NEW_ORDER_VALIDATOR = {
    'item_id': {
        'required': True,
        'type': 'integer',
        'coerce': int,
        'min': 1,
        'max': 99999
    },
    'quant': {
        'required': True,
        'type': 'integer',
        'coerce': int,
        'min': 0,
        'max': 99999999
    },
    'eta': {
        'required': True,
        'type': 'integer',
        'coerce': int,
        'min': int(time.time())
    }
}

# datetime 'regex': '^([0]\d|[1][0-2])\/([0-2]\d|[3][0-1])\/([2][01]|[1][6-9])\d{2}(\s([0-1]\d|[2][0-3])(\:[0-5]\d){1,2})?$'

EDIT_THRESH_VALIDATOR = {
    'item_id': {
        'required': True,
        'type': 'integer',
        'coerce': int,
        'min': 1,
        'max': 99999
    },
    'alert_thresh': {
        'required': True,
        'type': 'integer',
        'coerce': int,
        'min': 0,
        'max': 99999999
    },
    'id': {
        'required': False
    }
}

STATUS_CHANGE_VALIDATOR = {
    'order_id': {
        'required': True,
        'type': 'integer',
        'coerce': int,
        'min': 1,
        'max': 99999
    },
    'order_status': {
        'required': True,
        'type': 'string',
        'allowed': [
            'new',
            'pending',
            'shipped',
            'completed'
        ]
    }
}

GET_TAGS_VALIDATOR = {
    'query': {
        'required': True,
        'type': 'string',
        'allowed': ['list', 'tag', 'rel']
    },
    'tag': {
        'required': False,
        'type': 'string',
        'regex': r'^\w+$'
    }
}

DISTRIBUTOR_VALIDATOR = {
    'name': {
        'required': True,
        'type': 'string',
        'regex': r'^\w+$',
        'minlength': 2,
        'maxlength': 40
    },
    'email_address': {
        'required': False,
        'type': 'string',
        'regex': '^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))'
    },
    'phone_number': {
        'required': False,
        'type': 'integer',
        'coerce': int,
        'min': 100000000,
        'max': 999999999999
    }
}

EDIT_QUANT_VALIDATOR = {
    'item_id': {
        'required': True,
        'type': 'integer',
        'coerce': int,
        'min': 0,
        'max': 9999999
    },
    'quant': {
        'required': True,
        'type': 'integer',
        'coerce': int,
        'min': 0,
        'max': 9999999
    },
    'id': {
        'required': False
    }
}

RM_USER_VALIDATOR = {
    'user_id': {
        'required': True,
        'type': 'integer',
        'coerce': int,
        'min': 1,
        'max': 9999999
    }
}
RM_DIST_VALIDATOR = {
    'distributor_id': {
        'required': True,
        'type': 'integer',
        'coerce': int,
        'min': 1,
        'max': 9999999
    }
}

INVITE_VALIDATOR = {
    'invite_code': schemas['invite_code']
}

INVITE_VALIDATOR_EMAIL = {
    'email_address': {
        'required': True,
        'type': 'string',
        'regex': '^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))'
    },
    'invite_code': schemas['invite_code'],
    'auth_method': schemas['auth_method']
}
INVITE_VALIDATOR_PHONE = {
    'mobile_number_no': {
        'required': True,
        'type': 'string',
        'regex': '^[+]*[(]{0,1}[0-9]{1,4}[)]{0,1}[-\s\./0-9]*$'
    },
    'invite_code': schemas['invite_code'],
    'auth_method': schemas['auth_method']
}
