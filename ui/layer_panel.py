from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTreeWidget, QTreeWidgetItem, QLabel, QAbstractItemView
)
from PyQt6.QtGui import QColor, QBrush
from PyQt6.QtCore import Qt, pyqtSignal

from core.document import ColorLayer, Shape

# class LayerTreeWidget(QTreeWidget):
#     """
#     Restricts drag and drop to same-level nodes only:
#
#     - Color nodes  → reorder among top-level only
#     - Object nodes → reorder within or move between color nodes only
#     - Shape nodes  → cannot be dragged at all
#     """
#
#     def _get_type(self, item):
#         if item is None:
#             return None
#         data = item.data(0, Qt.ItemDataRole.UserRole)
#         return data.get("type") if data else None
#
#     def _drop_is_valid(self, event) -> bool:
#         source_type = self._get_type(self.currentItem())
#
#         # Shapes cannot be dragged at all
#         if source_type == "shape":
#             return False
#
#         target   = self.itemAt(event.position().toPoint())
#         position = self.dropIndicatorPosition()
#
#         # DropIndicatorPosition values:
#         # OnItem     = 0  (dropping onto an item)
#         # AboveItem  = 1  (dropping above an item)
#         # BelowItem  = 2  (dropping below an item)
#         # OnViewport = 3  (dropping onto empty space)
#
#         if source_type == "color":
#             # Color nodes can only be reordered at top level.
#             # Valid: dropping above/below another color node,
#             #        or onto viewport (end of list).
#             if position == QAbstractItemView.DropIndicatorPosition.OnItem:
#                 # Dropping ON an item — only valid if that item is also a color node
#                 return self._get_type(target) == "color"
#             if position == QAbstractItemView.DropIndicatorPosition.OnViewport:
#                 return True
#             # Above/below — valid only if the reference item is a color node
#             return self._get_type(target) == "color"
#
#         if source_type == "object":
#             # Object nodes can be reordered within a color node or moved
#             # to another color node.
#             # Valid: dropping ON a color node, or above/below an object node
#             #        (which means they share the same color parent).
#             if position == QAbstractItemView.DropIndicatorPosition.OnItem:
#                 return self._get_type(target) == "color"
#             if position == QAbstractItemView.DropIndicatorPosition.OnViewport:
#                 return False
#             # Above/below an item — valid if that item is an object node
#             return self._get_type(target) == "object"
#
#         return False
#
#     def dragMoveEvent(self, event):
#         if self._drop_is_valid(event):
#             super().dragMoveEvent(event)
#         else:
#             event.ignore()
#
#     def dropEvent(self, event):
#         if self._drop_is_valid(event):
#             super().dropEvent(event)
#         else:
#             event.ignore()

class LayerTreeWidget(QTreeWidget):
    """
    Two-level tree: ColorLayer nodes at top, Shape nodes as children.
    Drag/drop rules:
    - Color nodes: reorder among top level only
    - Shape nodes: reorder within or move between color nodes
    """

    def _get_type(self, item):
        if item is None:
            return None
        data = item.data(0, Qt.ItemDataRole.UserRole)
        return data.get("type") if data else None

    def _drop_is_valid(self, event) -> bool:
        source_type = self._get_type(self.currentItem())
        if source_type is None:
            return False

        target   = self.itemAt(event.position().toPoint())
        position = self.dropIndicatorPosition()

        if source_type == "color":
            if position == QAbstractItemView.DropIndicatorPosition.OnItem:
                return self._get_type(target) == "color"
            if position == QAbstractItemView.DropIndicatorPosition.OnViewport:
                return True
            return self._get_type(target) == "color"

        if source_type == "shape":
            if position == QAbstractItemView.DropIndicatorPosition.OnItem:
                return self._get_type(target) == "color"
            if position == QAbstractItemView.DropIndicatorPosition.OnViewport:
                return False
            return self._get_type(target) == "shape"

        return False

    def dragMoveEvent(self, event):
        if self._drop_is_valid(event):
            super().dragMoveEvent(event)
        else:
            event.ignore()

    def dropEvent(self, event):
        if self._drop_is_valid(event):
            super().dropEvent(event)
        else:
            event.ignore()

class LayerPanel(QWidget):

    # Emitted when a shape is removed — carries shape id
    shapes_removed = pyqtSignal(list)
    # Emitted when a color layer is removed — carries ColorLayer hex
    color_layer_removed = pyqtSignal(str)
    # Emitted when color node double-clicked — carries color hex string
    color_layer_settings = pyqtSignal(str)
    # emitted when a shape node is clicked — carries shape id
    shape_clicked = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(6)

        # Header label
        label = QLabel("Layers")
        label.setStyleSheet("font-weight: bold; font-size: 11px;")
        layout.addWidget(label)

        # Layer list
        self.tree = LayerTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            QTreeWidget::item {
                padding: 3px;
            }
            QTreeWidget::item:selected {
                background: #0F3460;
                color: white;
            }
        """)
        self.tree.itemClicked.connect(self._on_item_clicked)
        self.tree.itemDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self.tree)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_remove = QPushButton("− Remove")
        self.btn_remove.clicked.connect(self.remove_selected)
        btn_layout.addWidget(self.btn_remove)
        layout.addLayout(btn_layout)

    # ── Public API ─────────────────────────────────────────────────────────────

    def add_color_layer(self, color_layer: ColorLayer):
        """Add or refresh a color layer node and all its shapes."""
        node = self._find_color_node(color_layer.color)
        if node is None:
            node = self._create_color_node(color_layer)
        else:
            # Refresh label in case operation changed
            node.setText(0, color_layer.label)

        for shape in color_layer.shapes:
            self._add_shape_node(node, shape, color_layer.color)

        node.setExpanded(True)

    def add_shape(self, color_layer: ColorLayer, shape: Shape):
        """Add a single shape node under the correct color layer."""
        node = self._find_color_node(color_layer.color)
        if node is None:
            node = self._create_color_node(color_layer)
        self._add_shape_node(node, shape, color_layer.color)
        node.setExpanded(True)

    def remove_shape_node(self, shape_id: int):
        """Remove a shape node by shape id."""
        item = self._find_shape_node(shape_id)
        if item is None:
            return
        parent = item.parent()
        if parent:
            parent.removeChild(item)
            if parent.childCount() == 0:
                self.tree.invisibleRootItem().removeChild(parent)

    def select_shape_node(self, shape_id: int):
        """Highlight the shape node matching the given id."""
        self.tree.clearSelection()
        item = self._find_shape_node(shape_id)
        if item:
            self.tree.setCurrentItem(item)
            self.tree.scrollToItem(item)

    def sync_selection(self, shape_ids: list):
        """Highlight all tree nodes matching the given shape ids."""
        self.tree.clearSelection()
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        for shape_id in shape_ids:
            item = self._find_shape_node(shape_id)
            if item:
                self.tree.setCurrentItem(item)
                item.setSelected(True)
                # Only scroll to last one
        if shape_ids:
            last = self._find_shape_node(shape_ids[-1])
            if last:
                self.tree.scrollToItem(last)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

    def update_color_node_label(self, color_layer: ColorLayer):
        """Refresh label after settings change."""
        node = self._find_color_node(color_layer.color)
        if node:
            node.setText(0, color_layer.label)

    def move_shape_node(self, shape_id: int, new_color_layer: ColorLayer):
        """Move a shape node to a different color layer node."""
        item = self._find_shape_node(shape_id)
        if item is None:
            return
        old_parent = item.parent()

        # Remove from old parent
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if old_parent:
            old_parent.removeChild(item)
            if old_parent.childCount() == 0:
                self.tree.invisibleRootItem().removeChild(old_parent)

        # Add to new color node
        new_node = self._find_color_node(new_color_layer.color)
        if new_node is None:
            new_node = self._create_color_node(new_color_layer)

        # Update color in node data and re-add
        data["color"] = new_color_layer.color
        item.setData(0, Qt.ItemDataRole.UserRole, data)
        new_node.addChild(item)
        new_node.setExpanded(True)

    # ── Private Helpers ─────────────────────────────────────────────────────────────

    def _add_shape_node(self, parent_node, shape: Shape, color: str):
        """Create and add a shape node under a color node."""
        node = QTreeWidgetItem(parent_node)
        label = shape.source if shape.source else f"Shape {shape.id}"
        if shape.closed:
            label += " ●"
        node.setText(0, label)
        node.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "shape",
            "shape_id": shape.id,
            "color": color
        })
        return node

    def _find_color_node(self, color: str) -> QTreeWidgetItem | None:
        """Find an existing top-level color node by color hex."""
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get("color", "").upper() == color.upper():
                return item
        return None

    def _find_shape_node(self, shape_id: int):
        """Find an existing shape node by shape id."""

        for i in range(self.tree.topLevelItemCount()):
            color_node = self.tree.topLevelItem(i)
            for j in range(color_node.childCount()):
                shape_node = color_node.child(j)
                data = shape_node.data(0, Qt.ItemDataRole.UserRole)
                if data and data.get("shape_id") == shape_id:
                    return shape_node
        return None

    def _create_color_node(self, color_layer: ColorLayer) -> QTreeWidgetItem:
        """Create a new top-level color layer node."""
        node = QTreeWidgetItem(self.tree)
        node.setText(0, f"{color_layer.color.upper()}  |  {color_layer.operation}")
        node.setCheckState(0, Qt.CheckState.Checked)
        node.setForeground(0, QBrush(QColor(color_layer.color)))
        node.setData(0, Qt.ItemDataRole.UserRole, {
            "type":  "color",
            "color": color_layer.color
        })
        return node

    def _on_double_click(self, item, column):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("type") == "color":
            self.color_layer_settings.emit(data.get("color"))

    def _on_item_clicked(self, item, column):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("type") == "shape":
            self.shape_clicked.emit(data.get("shape_id"))

    # def remove_selected(self):
    #     """Remove the currently selected node and emit the appropriate signal."""
    #     item = self.tree.currentItem()
    #     if item is None:
    #         return
    #
    #     data = item.data(0, Qt.ItemDataRole.UserRole)
    #     if not data:
    #         return
    #
    #     node_type = data.get("type")
    #
    #     if node_type == "color":
    #         color = data.get("color")
    #         self.tree.invisibleRootItem().removeChild(item)
    #         self.color_layer_removed.emit(color)
    #
    #     elif node_type == "shape":
    #         shape_id = data.get("shape_id")
    #         parent = item.parent()
    #         if parent:
    #             parent.removeChild(item)
    #             if parent.childCount() == 0:
    #                 color = parent.data(0, Qt.ItemDataRole.UserRole).get("color")
    #                 self.tree.invisibleRootItem().removeChild(parent)
    #                 self.color_layer_removed.emit(color)
    #             else:
    #                 self.shape_removed.emit(shape_id)

    def remove_selected(self):
        """Remove all currently selected shape nodes."""
        shape_ids = []

        # Collect all selected shape ids
        for i in range(self.tree.topLevelItemCount()):
            color_node = self.tree.topLevelItem(i)
            for j in range(color_node.childCount() - 1, -1, -1):
                shape_node = color_node.child(j)
                data = shape_node.data(0, Qt.ItemDataRole.UserRole)
                if shape_node.isSelected() and data and data.get("type") == "shape":
                    shape_ids.append(data.get("shape_id"))

        if not shape_ids:
            return

        self.shapes_removed.emit(shape_ids)
