import abc
from enum import Enum
from typing import List, Optional


class DashboardAttributes(str, Enum):
    STUDY_CASE_ID = 'study_case_id'
    ID = 'id'
    ITEMS = 'items'


class DisplayableItemType(str, Enum):
    TEXT = 'text'
    GRAPH = 'graph'
    SECTION = 'section'
    VALUE = 'value'  # Not implemented yet


class Position:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y


class Size:
    def __init__(self, cols: int, rows: int):
        self.cols = cols
        self.rows = rows


class DisplayableItem(abc.ABC):
    def __init__(
            self,
            item_type: DisplayableItemType,
            position: Optional[Position] = None,
            size: Optional[Size] = None,
            data: Optional[dict] = None,
    ):
        self.item_type = item_type
        self.position = position
        self.size = size
        self.data = data or {}
        self.id = id

    @abc.abstractmethod
    def serialize(self) -> dict:
        pass


class DashboardText(DisplayableItem):
    def __init__(self, content: str, position: Position, size: Size):
        super().__init__(
            item_type=DisplayableItemType.TEXT,
            position=position,
            size=size,
            data={"content": content}
        )

    def serialize(self):
        return {
            "item_type": self.item_type,
            "position": self.position,
            "size": self.size,
            "data": self.data,
            "id": self.id,
        }


class DashboardGraph(DisplayableItem):
    def __init__(self, discipline_name: str, name: str, plot_index: int, graph_data: dict, position: Position,
                 size: Size):
        self.discipline_name = discipline_name
        self.name = name
        self.plot_index = plot_index
        super().__init__(
            item_type=DisplayableItemType.GRAPH,
            position=position,
            size=size,
            data={"graphData": graph_data}
        )

    def serialize(self):
        return {
            "discipline_name": self.discipline_name,
            "name": self.name,
            "plot_index": self.plot_index,
            "data": self.data,
            "item_type": self.item_type,
            "position": self.position,
            "size": self.size,
        }

    @property
    def identifier(self) -> str:
        return f"{self.discipline_name}-{self.name}-{self.plot_index}"

class ValueData:
    def __init__(
            self,
            nodeData: Dict = None,
            namespace: str = None,
            discipline: str = None
    ):
        self.nodeData = nodeData if nodeData is not None else {}
        self.namespace = namespace
        self.discipline = discipline

    def serialize(self) -> dict:
        return {
            "nodeData": self.nodeData,
            "namespace": self.namespace,
            "discipline": self.discipline
        }

class DashboardSection(DisplayableItem):
    def __init__(self, title: str, position: Position, size: Size, children: List[DisplayableItem]):
        super().__init__(
            item_type=DisplayableItemType.SECTION,
            position=position,
            size=size,
            data={"title": title, "children": children}
        )

    def serialize(self):
        return {
            "item_type": self.item_type,
            "position": self.position,
            "size": self.size,
            "id": self.id,
            "data": self.data,
        }


class Dashboard:
    def __init__(self, study_case_id: int, items: List[DisplayableItem]):
        self.study_id = study_case_id
        self.items = items

    def serialize(self):
        return {
            "study_case_id": self.study_id,
            "items": [item.serialize() for item in self.items],
        }

    @classmethod
    def deserialize(cls, json_data: dict) -> Dashboard:
        """
        Create a Dashboard instance from JSON data
        """
        study_case_id = json_data.get(DashboardAttributes.STUDY_CASE_ID.value)
        layout_data = json_data.get(DashboardAttributes.LAYOUT.value, {})
        data_data = json_data.get(DashboardAttributes.DATA.value, {})

        layout = {}
        data = {}

        # process layout and data
        for key, value in layout_data.items():
            item_id = value.get('item_id')
            item_type = DisplayableItemType(value.get('item_type'))
            layout[key] = ItemLayout(
                item_id=item_id,
                item_type=item_type,
                x=int(value.get('x', 0)),
                y=int(value.get('y', 0)),
                cols=int(value.get('cols', 1)),
                rows=int(value.get('rows', 1)),
                minCols=int(value.get('minCols', 1)),
                minRows=int(value.get('minRows', 1))
            )
            if 'children' in value:
                layout[key].children = value['children']
            if key in data_data:
                item_data = data_data[key]
                if item_type == DisplayableItemType.TEXT:
                    data[key] = TextData(content=item_data.get('content', ''))
                elif item_type == DisplayableItemType.GRAPH:
                    data[key] = GraphData(
                        disciplineName=item_data.get('disciplineName', ''),
                        name=item_data.get('name', ''),
                        plotIndex=int(item_data.get('plotIndex', 0)),
                        postProcessingFilters=item_data.get('postProcessingFilters', []),
                        graphData=item_data.get('graphData', {}),
                        title=item_data.get('title')
                    )
                elif item_type == DisplayableItemType.SECTION:
                    data[key] = SectionData(
                        title=item_data.get('title', ''),
                        shown=item_data.get('shown', True),
                        expandedSize=item_data.get('expandedSize')
                    )

        for data_key in data_data.keys():
            if data_key not in layout:
                item_data = data_data[data_key]
                if 'content' in item_data:
                    data[data_key] = TextData(content=item_data.get('content', ''))
                else:
                    data[data_key] = GraphData(
                        disciplineName=item_data.get('disciplineName', ''),
                        name=item_data.get('name', ''),
                        plotIndex=int(item_data.get('plotIndex', 0)),
                        postProcessingFilters=item_data.get('postProcessingFilters', []),
                        graphData=item_data.get('graphData', {}),
                        title=item_data.get('title')
                    )

        return cls(study_case_id=study_case_id, layout=layout, data=data)

def detect_dashboard_structure(json_data: dict) -> str:
    """
    Detect if dashboard uses old or new structure
    """
    if 'items' in json_data and isinstance(json_data['items'], List):
        return 'old'
    elif 'layout' in json_data and 'data' in json_data and isinstance(json_data['layout'], dict) and isinstance(json_data['data'], dict):
        return 'new'
    else:
        return 'unknown'

def migrate_from_old_format(dashboard_json):
    """
    Migrate old dashboard data format to the new format.
    This method assumes that the old format has a specific structure that needs to be transformed.
    """
    old_data = json.loads(dashboard_json) if isinstance(dashboard_json, str) else dashboard_json

    new_dashboard = {
        'study_case_id': old_data.get(DashboardAttributes.STUDY_CASE_ID.value, 0),
        'layout': {},
        'data': {}
    }
    old_items = old_data.get('items', [])

    for old_item in old_items:
        item_type = old_item.get('type')
        if item_type == DisplayableItemType.GRAPH:
            # not possible to migrate graph item -> lacking filters to create the new item_id
            continue
        layout, data = migrate_item_by_type(old_item)
        item_id = layout['item_id']
        new_dashboard['layout'][item_id] = layout
        new_dashboard['data'][item_id] = data
        if item_type == DisplayableItemType.SECTION:
            old_section_items = old_item.get('data', {}).get('items', [])
            for child_item in old_section_items:
                if item_type == DisplayableItemType.GRAPH:
                    # not possible to migrate graph item -> lacking filters to create the new item_id
                    continue
                child_layout, child_data = migrate_item_by_type(child_item)
                new_dashboard['data'][child_item.get('id')] = child_data

    return new_dashboard

def migrate_item_by_type(old_item):
    """
    Helper function to migrate item base on its type
    """
    item_type = old_item.get('type')
    if item_type == DisplayableItemType.TEXT:
        return migrate_text_item(old_item)
    elif item_type == DisplayableItemType.SECTION:
        return migrate_section_item(old_item)
    elif item_type == DisplayableItemType.VALUE:
        return migrate_value_item(old_item)
    elif item_type == DisplayableItemType.GRAPH:
        return migrate_graph_item(old_item)
    else:
        raise ValueError(f"Unknown item type: {item_type}")

def migrate_text_item(old_item):
    """
    Migrate a text item from the old format to the new format.
    """
    item_id = old_item.get('id', f"text_{int(time.time() * 1000)}")
    layout = {
        'item_id': item_id,
        'item_type': DisplayableItemType.TEXT.value,
        'x': old_item.get('x', 0),
        'y': old_item.get('y', 0),
        'cols': old_item.get('cols', 12),
        'rows': old_item.get('rows', 8),
        'minCols': old_item.get('minCols', 1),
        'minRows': old_item.get('minRows', 1),
    }

    data = {
        'content': old_item.get('data', {}).get('content', '')
    }

    return layout, data

def migrate_graph_item(old_item):
    """
    Migrate a graph item from the old format to the new format.
    """
    item_id = old_item.get('id')
    layout = {
        'item_id': item_id,
        'item_type': DisplayableItemType.GRAPH.value,
        'x': old_item.get('x', 0),
        'y': old_item.get('y', 0),
        'cols': old_item.get('cols', 16),
        'rows': old_item.get('rows', 12),
        'minCols': old_item.get('minCols', 12),
        'minRows': old_item.get('minRows', 8),
    }
    data = {
        'disciplineName': old_item.get('data', {}).get('disciplineName', ''),
        'name': old_item.get('data', {}).get('name', ''),
        'plotIndex': old_item.get('data', {}).get('plotIndex', 0),
        'postProcessingFilters': old_item.get('data', {}).get('postProcessingFilters', []),
        'graphData': old_item.get('data', {}).get('graphData', {}),
        'title': old_item.get('data', {}).get('title')
    }
    return layout, data

def migrate_value_item(old_item):
    """
    Migrate a value item from the old format to the new format.
    """
    item_id = old_item.get('id', f"value_{int(time.time() * 1000)}")
    layout = {
        'item_id': item_id,
        'item_type': DisplayableItemType.VALUE.value,
        'x': old_item.get('x', 0),
        'y': old_item.get('y', 0),
        'cols': old_item.get('cols', 8),
        'rows': old_item.get('rows', 3),
        'minCols': old_item.get('minCols', 4),
        'minRows': old_item.get('minRows', 2),
    }

    data = {
        'nodeData': old_item.get('data', {}).get('nodeData', {}),
        'namespace': old_item.get('data', {}).get('namespace', ''),
        'discipline': old_item.get('data', {}).get('discipline', '')
    }

    return layout, data

def migrate_section_item(old_item):
    """
    Migrate a section item from the old format to the new format.
    """
    item_id = old_item.get('id', f"section_{int(time.time() * 1000)}")
    children_ids = []
    old_section_items = old_item.get('data', {}).get('items', [])
    for child_item in old_section_items:
        if child_item.get('type') == DisplayableItemType.GRAPH:
            # not possible to migrate graph item -> lacking filters to create the new item_id
            continue
        child_id = child_item.get('id')
        if child_id:
            children_ids.append(child_id)

    layout = {
        'item_id': item_id,
        'item_type': DisplayableItemType.SECTION.value,
        'x': old_item.get('x', 0),
        'y': old_item.get('y', 0),
        'cols': old_item.get('cols', 40),
        'rows': old_item.get('rows', 20),
        'minCols': old_item.get('minCols', 40),
        'minRows': old_item.get('minRows', 16),
        'children': children_ids
    }

    old_section_data = old_item.get('data', {})
    data = {
        'title': old_section_data.get('title', ''),
        'shown': old_section_data.get('shown', True),
        'expandedSize': old_section_data.get('expandedSize')
    }

    return layout, data
