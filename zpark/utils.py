
def obj_to_dict(obj):
    """
    Converts an object to a dict by taking the object's properties and
    variables and their values and putting them into a dict. Private
    and dunder ('__') properties are ignored.

    The use case for this is to enable passing of an object's data across
    the app/task barrier in a format that is serializable by a JSON-based
    serializer.

    Args:
        - obj: An opaque object

    Returns:
        - A dict
    """

    return {
        attr:getattr(obj, attr)
            for attr in dir(obj)
            if not attr.startswith('_')
    }
