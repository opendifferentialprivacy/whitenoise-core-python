import subprocess
import queue
import os

from burdock.wrapper import LibraryWrapper

# protoc must be installed and on path
subprocess.call(f"protoc --python_out={os.getcwd()} *.proto", shell=True, cwd=os.path.abspath('../prototypes/'))

# these modules are generated via the subprocess call
import analysis_pb2
import types_pb2
import release_pb2

core_wrapper = LibraryWrapper(validator='HASKELL', runtime='RUST')


class Component(object):
    def __init__(self, name: str, arguments: dict = None, options: dict = None):
        self.name: str = name
        self.arguments: dict = arguments or {}
        self.options: dict = options

        global context
        if context:
            context.components.append(self)

    def __add__(self, other):
        return Component('Add', {'left': self, 'right': other})

    def __sub__(self, other):
        return Component('Add', {'left': self, 'right': -other})

    def __neg__(self):
        return Component('Negate', {'data': self})


def mean(data):
    return Component('Mean', {'data': data})


def dp_mean_laplace(data, epsilon, minimum=None, maximum=None, num_records=None):

    # TODO: recursively extract from child? potentially implement in validator, or runtime?
    # if minimum is None:
    #     minimum =
    return Component('DPMeanLaplace', {
        'data': data,
        'num_records': Component('Literal', options={'numeric': num_records}),
        'minimum': Component('Literal', options={'numeric': minimum}),
        'maximum': Component('Literal', options={'numeric': maximum})
    }, {'epsilon': epsilon})


class Analysis(object):
    def __init__(self, *components, distance='APPROXIMATE', neighboring='SUBSTITUTE'):
        self.components: list = list(components)
        self.release_proto: release_pb2.Release = None
        self.distance: str = distance
        self.neighboring: str = neighboring

        self._context_cache = None

    def _make_analysis_proto(self):

        id_count = 0

        discovered_components = {}
        component_queue = queue.Queue()

        def enqueue(component):
            if component in discovered_components:
                return discovered_components[component]

            nonlocal id_count
            id_count += 1

            discovered_components[component] = id_count
            component_queue.put({'component_id': id_count, 'component': component})

            return id_count

        for component in self.components:
            enqueue(component)

        vertices = {}

        while not component_queue.empty():
            item = component_queue.get()
            component = item['component']
            component_id = item['component_id']

            vertices[component_id] = analysis_pb2.Component(**{
                'arguments': {
                    name: analysis_pb2.Component.Field(
                        source_node_id=enqueue(component_child),
                        # TODO: this is not always necessarily data! if a component has multiple outputs...
                        source_field="data"
                    ) for name, component_child in component.arguments.items()
                },
                component.name.lower():
                    getattr(analysis_pb2, component.name)(**(component.options or {}))
            })

        return analysis_pb2.Analysis(
            graph=vertices,
            definition=types_pb2.PrivacyDefinition(
                distance=types_pb2.PrivacyDefinition.Distance.Value(self.distance),
                neighboring=types_pb2.PrivacyDefinition.Neighboring.Value(self.neighboring)
            )
        )

    def _make_release_proto(self):
        return self.release_proto or release_pb2.Release()

    def validate(self):
        return core_wrapper.validateAnalysis(
            self._make_analysis_proto())

    @property
    def epsilon(self):
        return core_wrapper.computeEpsilon(
            self._make_analysis_proto())

    def release(self, data):
        analysis_proto = self._make_analysis_proto()

        self.release_proto: release_pb2.Release = core_wrapper.computeRelease(
            analysis_proto,
            self._make_release_proto(),
            data)

        return core_wrapper.generateReport(
            analysis_proto,
            self._make_release_proto())

    def __enter__(self):
        global context
        self._context = context
        context = self
        return context

    def __exit__(self, exc_type, exc_val, exc_tb):
        global context
        context = self._context

    def plot(self):
        import networkx as nx
        import matplotlib.pyplot as plt

        analysis = self._make_analysis_proto()
        graph = nx.DiGraph()

        def label(node_id):
            return f'{node_id} {analysis.graph[node_id].WhichOneof("value")}'

        for nodeId, component in list(analysis.graph.items()):
            for field in component.arguments.values():
                graph.add_edge(label(field.source_node_id), label(nodeId))

        nx.draw(graph, with_labels=True, node_color='white')
        plt.pause(.001)

# sugary syntax for managing analysis contexts
context = None