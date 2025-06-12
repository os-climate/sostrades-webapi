'''
Copyright 2025 Capgemini

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''

import abc
from enum import Enum
from typing import List, Optional, Union, Dict, Any

class DashboardAttributes(str, Enum):
    STUDY_CASE_ID = 'study_case_id'
    ITEMS = 'items'


class DisplayableItemType(str, Enum):
    TEXT = 'text'
    GRAPH = 'graph'
    SECTION = 'section'


class BaseItem(abc.ABC):
    def __init__(
            self,
            item_id: str,
            item_type: DisplayableItemType,
            x: int,
            y: int,
            cols: int,
            rows: int,
            min_cols: int,
            min_rows: int,
            data: Dict[str, Any],
            max_rows: Optional[int] = None
    ):
        self.id = item_id
        self.type = item_type
        self.x = x
        self.y = y
        self.cols = cols
        self.rows = rows
        self.min_cols = min_cols
        self.min_rows = min_rows
        self.data = data
        if max_rows:
            self.max_rows = max_rows

    @abc.abstractmethod
    def serialize(self) -> dict:
        pass


class DashboardText(BaseItem):
    def __init__(self, content: str = '', item_id: Optional[str] = None, x: int = 0, y: int = 0):
        super().__init__(
            item_id=item_id,
            item_type=DisplayableItemType.TEXT,
            x=x,
            y=y,
            cols=3,
            rows=2,
            min_cols=1,
            min_rows=1,
            data={"content": content}
        )

    def serialize(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "x": self.x,
            "y": self.y,
            "cols": self.cols,
            "rows": self.rows,
            "min_cols": self.min_cols,
            "min_rows": self.min_rows,
            "data": self.data,
        }


class DashboardGraph(BaseItem):
    def __init__(self, discipline_name: str, name: str, plot_index: int, graph_data: dict, x: int = 0, y: int = 0):
        self.discipline_name = discipline_name
        self.name = name
        self.plot_index = plot_index
        item_id = f"{discipline_name}-{name}-{plot_index}"
        super().__init__(
            item_id=item_id,
            item_type=DisplayableItemType.GRAPH,
            x=x,
            y=y,
            cols=4,
            rows=3,
            min_cols=3,
            min_rows=2,
            data={"graphData": graph_data}
        )

    @property
    def identifier(self) -> str:
        return f"{self.discipline_name}-{self.name}-{self.plot_index}"

    @property
    def get_title(self) -> str:
        import re
        title = self.data["graphData"]["layout"]["title"]["text"]
        return re.sub(r'<[^>]*>', '', title)

    def serialize(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "x": self.x,
            "y": self.y,
            "cols": self.cols,
            "rows": self.rows,
            "min_cols": self.min_cols,
            "min_rows": self.min_rows,
            "discipline_name": self.discipline_name,
            "name": self.name,
            "plot_index": self.plot_index,
            "data": self.data
        }


class DashboardSection(BaseItem):
    def __init__(self,
                 title: str = '',
                 items: List[Union['DashboardText', 'DashboardGraph', 'DashboardSection']] = None,
                 shown: bool = True,
                 expanded_size: Optional[int] = None,
                 x: int = 0,
                 y: int = 0,
                 item_id: Optional[str] = None
    ):
        if items is None:
            items = []

        if item_id is None:
            import time
            item_id = f"section-{int(time.time() * 1000)}"

        super().__init__(
            item_id=item_id,
            item_type=DisplayableItemType.SECTION,
            x=x,
            y=y,
            cols=10,
            rows=5,
            min_cols=10,
            min_rows=4,
            data={"title": title, "items": items, "shown": shown}
        )

        if expanded_size is not None:
            self.data["expanded_size"] = expanded_size

    def serialize(self) -> dict:
        serialized_items = []
        for item in self.data["items"]:
            if isinstance(item, (DashboardText, DashboardGraph, DashboardSection)):
                serialized_items.append(item.serialize())
            else:
                serialized_items.append(item)
        result = {
            "id": self.id,
            "type": self.type,
            "x": self.x,
            "y": self.y,
            "cols": self.cols,
            "rows": self.rows,
            "min_cols": self.min_cols,
            "min_rows": self.min_rows,
            "data": {
                "title": self.data["title"],
                "items": serialized_items,
                "shown": self.data.get["shown"],
            },
        }

        if expanded_size is self.data:
            result["data"]["expanded_size"] = self.data["expanded_size"]

        if hasattr(self, 'max_rows'):
            result["max_rows"] = self.max_rows

        return result


class Dashboard:
    def __init__(self, study_case_id: int, items: List[Union[DashboardText, DashboardGraph, DashboardSection]]):
        self.study_id = study_case_id
        self.items = items

    def serialize(self) -> dict:
        return {
            "study_case_id": self.study_id,
            "items": [item.serialize() for item in self.items],
        }

    @classmethod
    def create(cls, json_data: dict) -> 'Dashboard':
        """ create a Dashboard instance from JSON data"""
        study_case_id = json_data.get(DashboardAttributes.STUDY_CASE_ID.value)
        items_data = json_data.get(DashboardAttributes.ITEMS.value, [])

        items = []
        for item_data in items_data:
            item_type = item_data.get("type")
            if item_type == DisplayableItemType.TEXT.value:
                item = DashboardText(content=item_data["data"].get("content", ""), item_id=item_data.get("id"), x=item_data.get("x", 0), y=item_data.get("y", 0))
                item.cols = item_data.get("cols", 3)
                item.rows = item_data.get("rows", 2)
                item.min_cols = item_data.get("min_cols", 1)
                item.min_rows = item_data.get("min_rows", 1)
                items.append(item)
                # items.append(DashboardText(**item_data))
            elif item_type == DisplayableItemType.GRAPH.value:
                item = DashboardGraph(
                    discipline_name=item_data.get("discipline_name", ""),
                    name=item_data.get("name", ""),
                    plot_index=item_data.get("plot_index", 0),
                    graph_data=item_data.get("data", {}).get("graphData", {}),
                    x=item_data.get("x", 0),
                    y=item_data.get("y", 0),
                )
                item.cols = item_data.get("cols", 4)
                item.rows = item_data.get("rows", 3)
                item.min_cols = item_data.get("min_cols", 3)
                item.min_rows = item_data.get("min_rows", 2)
                items.append(item)
                # items.append(DashboardGraph(**item_data))
            elif item_type == DisplayableItemType.SECTION.value:
                section_items = []
                for section_item_data in item_data["data"].get("items", []):
                    section_item_type = section_item_data.get("type")
                    if section_item_type == DisplayableItemType.TEXT.value:
                        section_item = DashboardText(
                            content=section_item_data["data"].get("content", ""),
                            item_id=section_item_data.get("id"),
                            x=section_item_data.get("x", 0),
                            y=section_item_data.get("y", 0),
                        )
                        section_item.cols = section_item_data.get("cols", 3)
                        section_item.rows = section_item_data.get("rows", 2)
                        section_item.min_cols = section_item_data.get("min_cols", 1)
                        section_item.min_rows = section_item_data.get("min_rows", 1)
                        section_items.append(section_item)
                    elif section_item_type == DisplayableItemType.GRAPH.value:
                        section_item = DashboardGraph(
                            discipline_name=section_item_data.get("discipline_name", ""),
                            name=section_item_data.get("name", ""),
                            plot_index=section_item_data.get("plot_index", 0),
                            graph_data=section_item_data.get("data", {}).get("graphData", {}),
                            x=section_item_data.get("x", 0),
                            y=section_item_data.get("y", 0)
                        )
                        section_item.cols = section_item_data.get("cols", 4)
                        section_item.rows = section_item_data.get("rows", 3)
                        section_item.min_cols = section_item_data.get("min_cols", 3)
                        section_item.min_rows = section_item_data.get("min_rows", 2)
                        section_items.append(section_item)
                item = DashboardSection(
                    title=item_data["data"].get("title", ""),
                    items=section_items,
                    shown=item_data["data"].get("shown", True),
                    expanded_size=item_data["data"].get("expanded_size"),
                    x=item_data.get("x", 0),
                    y=item_data.get("y", 0),
                    item_id=item_data.get("id")
                )
                item.cols = item_data.get("cols", 10)
                item.rows = item_data.get("rows", 5)
                item.min_cols = item_data.get("min_cols", 10)
                item.min_rows = item_data.get("min_rows", 4)
                if "max_rows" in item_data:
                    item.max_rows = item_data["max_rows"]
                items.append(item)
                # items.append(DashboardSection(**item_data))
            else:
                raise ValueError(f"Unknown item type: {item_type}")
        return cls(study_case_id, items)