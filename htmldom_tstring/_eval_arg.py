# import ast
# from numbers import Number


# def eval_constant_arg(value: str):
#     try:
#         return {
#             'None': None,
#             'True': True,
#             'False': False
#         }[value]
#     except KeyError:
#         pass
#     if value.isidentifier():
#         return value
#     try:
#         v = ast.literal_eval(value)
#     except Exception:
#         return value
    
#     if isinstance(v, (Number, str)):
#         return v
#     return value