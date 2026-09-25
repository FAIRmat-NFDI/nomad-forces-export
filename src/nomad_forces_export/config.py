VALID_FORMATS = {'ase_db', 'extxyz'}
VALID_PROPERTIES = {'energy', 'forces', 'stress'}

NOMAD_BASE_URL = 'https://nomad-lab.eu/prod/v1/api/v1'

WORKFLOWS = [
    'SinglePoint',
    'single_point',
    'GeometryOptimization',
    'geometry_optimization',
]

REQUIRED_METADATA = [
    'entry_id',
    'upload_id',
]
REQUIRED_SEARCH_QUANTITIES = {
    'metadata': {'entry_id': '*', 'upload_id': '*'},
    'results': {
        'method': {'method_name': '*', 'workflow_name': '*'},
    },
}
REQUIRED_ARCHIVE_DATA = {
    'metadata': {'entry_id': '*', 'upload_id': '*'},
    'results': {
        'method': '*',
    },
    'workflow2': {'results': {'is_converged_geometry': '*'}},
    'workflow': {
        'geometry_optimization': {'is_converged_geometry': '*'},
        'type': '*',
        'single_point': {'is_converged': '*'},
    },
    'run': {
        'program': '*',
        'method': '*',
        'system': {'atoms': '*', 'is_representative': '*'},
        'calculation': {
            'energy': '*',
            'forces': '*',
            'stress': '*',
            'system_ref': '*',
        },
    },
}

BASE_QUERY = {
    'results.method.method_name:any': ['DFT'],
    # "results.method.workflow_name:any": WORKFLOWS,
    'quantities:all': ['run.calculation', 'run.system'],
}

QUERY = {
    'and': [
        BASE_QUERY,
        {
            'or': [
                {
                    'and': [
                        {'quantities:all': ['workflow']},
                        {'quantities:none': ['results.method.workflow_name']},
                    ]
                },
                {'results.method.workflow_name:any': WORKFLOWS},
            ]
        },
    ]
}


def archive_filter(archive_entry: dict) -> bool:
    entry = archive_entry.get('archive', {})
    if (
        entry.get('results', {}).get('method', {}).get('workflow_name') not in WORKFLOWS
        and entry.get('workflow', [{}])[0].get('type') not in WORKFLOWS
    ):
        return True
    return False


# "query":
#         {
#   "and": [
#     {
#       "results.method.method_name:any": [
#         "DFT"
#       ],
#       "quantities:all": [
#         "run.calculation",
#         "run.system"
#       ]
#     },
#     {
#       "or": [
#         {
#           "and": [
#             {
#               "quantities:all": [
#                 "workflow"
#               ]
#             },
#             {
#               "quantities:none": [
#                 "results.method.workflow_name"
#               ]
#             }
#           ]
#         },
#         {
#           "results.method.workflow_name:any": [
#             "SinglePoint",
#             "single_point",
#             "GeometryOptimization",
#             "geometry_optimization"
#           ]
#         }
#       ]
#     }
#   ]
# }
