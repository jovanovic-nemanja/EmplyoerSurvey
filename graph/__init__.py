from common import log
from mo_dots import to_data


def load_edge_collection(col1, col2, _graph, from_vert_col=None, to_vert_col=None):
    edge_col_name = f"{col1}Of{col2}"
    if _graph.has_edge_collection(edge_col_name):
        return _graph.edge_collection(edge_col_name)
    else:
        return _graph.create_edge_definition(
            edge_collection=edge_col_name,
            from_vertex_collections=[from_vert_col or col2],
            to_vertex_collections=[to_vert_col or col1]
        )


def load_graph(_arango, _graph_name, _fresh=False):
    if _arango.has_graph(_graph_name):
        if not _fresh:
            return _arango.graph(_graph_name)
        _arango.delete_graph(_graph_name)
    return _arango.create_graph(_graph_name)


def load_collections(_graph, _collection_names, _col_type='vertex', _fresh=True):
    _res = {}
    _suffix = 'collection'  # if _col_type == 'vertex' else 'definition'
    has_collection = getattr(_graph, f'has_{_col_type}_{_suffix}')
    delete_collection = getattr(_graph, f'delete_{_col_type}_{_suffix}')
    get_collection = getattr(_graph, f'{_col_type}_{_suffix}')
    create_collection = getattr(_graph, f'create_{_col_type}_{_suffix}')
    for _col_args in _collection_names:
        try:
            if has_collection(_col_args[0]):
                if _fresh:
                    delete_collection(_col_args[0])
                _res[_col_args[0]] = get_collection(_col_args[0])
            else:
                _res[_col_args[0]] = create_collection(*_col_args)
        except Exception as ex:
            log.exception(ex)
    return to_data(_res)
