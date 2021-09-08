"""arango_client = ArangoClient(
            hosts=f"http://{ENV.ARANGO_HOST}:{ENV.ARANGO_PORT}"
        )
        app['arango'] = arango_client.db(ENV.ARANGO_DB,
                                         username=ENV.ARANGO_USER,
                                         password=ENV.ARANGO_PASSWORD)
        graph_name = ENV.ARANGO_GRAPH_NAME
        app['argon2'] = CryptContext(schemes=["argon2"])
        fresh = False
        graph = None
        try:
            graph = load_graph(app['arango'], graph_name)
            app['graph'] = graph
        except Exception as ex:
            log.exception(ex)
        vtx_collections = load_collections(graph, [
            ('Company',),
            ('Employee',),
            ('Question',),
            (ENV.ARANGO_GRAPH_ROOT,)
        ], _fresh=fresh)
        app['vtx_collections'] = vtx_collections
        company_of_site = load_edge_collection('Company', ENV.ARANGO_GRAPH_ROOT, graph)
        app['company_of_site'] = company_of_site
        vtx_collections[ENV.SITE_NAME].insert({
            '_key': '1',
            'node_name': f"{ENV.ARANGO_GRAPH_ROOT}Root"
        })
        employee_of_company = load_edge_collection('Employee', 'Company', graph)
        app['employee_of_company'] = employee_of_company
        question_of_employee = load_edge_collection('Question', 'Employee', graph)
        app['question_of_employee'] = question_of_employee
        log.info(f'Graph {graph_name} loaded.')"""
