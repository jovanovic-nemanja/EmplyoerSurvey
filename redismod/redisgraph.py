import asyncio
import aioredis

from redisgraph import Graph, Node, Edge

graph_name = "testgraph"

# define a list of edges
edges = [
    ('a', 'b', {"weight": 1}),
    ('a', 'c', {"weight": 2})
]

loop = asyncio.get_event_loop()


class AsyncGraph(Graph):
    '''
    Extends redisgraph.Graph to work with asyncio
    '''
    
    async def commit(self):
        """
        Create entire graph.
        """
        query = 'CREATE '
        for _, node in self.nodes.items():
            query += str(node) + ','
        
        for edge in self.edges:
            query += str(edge) + ','
        
        # Discard leading comma.
        if query[-1] is ',':
            query = query[:-1]
        
        return await self.query(query)
    
    def parse_string_to_value(self, s):
        try:
            return int(s)
        except ValueError:
            try:
                return float(s)
            except ValueError:
                return s
    
    async def query(self, q, print_stats=True):
        """
        Executes a query against the graph.
        """
        
        data, statistics = await self.redis_con.execute("GRAPH.QUERY", self.name, q)
        
        result_set = [res.decode().rstrip('\x00').replace('"', '').split(',') for res in data]
        result_keys = result_set[0]
        # TODO parse result keys into hierarchical records
        print([k.split('.') for k in result_keys])
        
        if (print_stats):
            for stat in statistics:
                print(stat.decode())
        return [dict(zip(result_keys, [self.parse_string_to_value(v) for v in result])) for result in result_set[1:]]


async def go():
    conn = await aioredis.create_connection(('localhost', 6379), loop=loop)
    
    redis_graph = AsyncGraph(graph_name, conn)
    for node_a_alias, node_b_alias, attrs in edges:
        print(node_a_alias, node_b_alias, attrs)
        node_a = Node(alias=node_a_alias, label="test", properties={'name': node_a_alias, "other": 1})
        node_b = Node(alias=node_b_alias, label="test", properties={'name': node_b_alias, "other": 2})
        redis_graph.add_node(node_a)
        redis_graph.add_node(node_b)
        
        redis_graph.add_edge(Edge(node_a, 'connects', node_b, properties=attrs))
    await redis_graph.commit()
    
    results = await redis_graph.query("MATCH (n)-[r]->(m) return n,m")
    
    conn.close()
    await conn.wait_closed()

# loop.run_until_complete(go())
