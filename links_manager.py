bl_info = {
    "name": "Links Manager",
    "author": "Sintesi Labs Design GmbH",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "3D Viewport > Sidebar > Links Manager",
    "description": "Adds a UI panel to quickly see, reload, open and find linked libraries",
    "wiki_url": "https://github.com/sintesilabs/blender-links-manager",
    "category": "Data"
}


import bpy
from bpy import props


# FUNCTIONS

def reload_linked(linked_list):
    '''Reload every linked library inside a target list'''

    successes = 0
    failures = 0

    for lib in linked_list:
        try:
            lib.reload()
            successes += 1
        except RuntimeError:
            failures += 1

    return successes, failures


def get_linked_libraries():
    '''Returns a list of linked libraries used in the current scene'''
    linked_libs = bpy.data.libraries

    return linked_libs


def get_target_lib(target_lib_index):
    '''Returns a specific linked library given an index argument'''
    linked_libs = get_linked_libraries()
    target_lib = linked_libs[target_lib_index]

    return target_lib


def delete_target_lib(target_lib):
    '''Delete the target Linked Library'''
    bpy.data.batch_remove(ids=(target_lib,))


def open_target_lib(target_lib_index):
    '''Open a new Blender instance of the target linked library'''
    linked_libs = get_linked_libraries()
    target_lib = linked_libs[target_lib_index]
    target_filepath = target_lib.filepath
    target_abspath = bpy.path.abspath(target_filepath)

    import subprocess

    subprocess.Popen(['blender', target_abspath])

    return target_abspath


# OPERATORS

class DATA_OT_reload_all_linked(bpy.types.Operator):
    '''Reload all linked libraries in the current scene'''

    bl_idname = "data.reload_all_linked"
    bl_label = "Reload All Linked"
    bl_description = "Reload all linked libraries"

    def execute(self, context):
        linked_libs = get_linked_libraries()
        successes, failures = reload_linked(linked_libs)

        if failures and successes:
            self.report(
            {"WARNING"},
            "Reloaded {suc} Linked {suc_num}, Failed to load {fail} Linked {fail_num}".format(
            suc = successes,
            suc_num = "Library" if successes == 1 else "Libraries",
            fail = failures,
            fail_num = "Library" if failures == 1 else "Libraries",
            )
            )
        elif not successes:
            self.report({"ERROR"}, f"Failed to reload {failures} Linked Libraries")
        else:
            self.report({"INFO"}, f"Reloaded {successes} Linked Libraries")

        return {"FINISHED"}


class DATA_OT_reload_linked(bpy.types.Operator):
    '''Reload a specific Linked Library'''

    bl_idname = "data.reload_linked"
    bl_label = "Reload Linked"
    bl_description = "Reload linked library"

    target_lib_index : props.IntProperty(name="Target Library", default=0)

    def execute(self, context):
        target_lib = get_target_lib(self.target_lib_index)
        successes, failures = reload_linked([target_lib])

        if not failures:
            self.report({"INFO"}, f"Linked Library Reloaded: {target_lib.name}")
        else:
            self.report({"ERROR"}, "Failed to reload this library")

        return {"FINISHED"}


class DATA_OT_delete_linked(bpy.types.Operator):
    '''Delete a specific Linked Library'''

    bl_idname = "data.delete_linked"
    bl_label = "Delete Linked"
    bl_description = "Delete linked library"

    target_lib_index : props.IntProperty(name="Target Library", default=0)

    def execute(self, context):
        target_lib = get_target_lib(self.target_lib_index)

        self.report({"INFO"}, f"Linked Library Deleted: {target_lib.name}")

        delete_target_lib(target_lib)

        return {"FINISHED"}


class DATA_OT_open_linked(bpy.types.Operator):
    '''Open a specific Linked Library in a new Blender instance '''

    bl_idname = "data.open_linked"
    bl_label = "Open Linked Library"
    bl_description = "Open the linked library in a new Blender instance"

    target_lib_index : props.IntProperty(name="Target Library", default=0)

    def execute(self, context):
        target_abspath = open_target_lib(self.target_lib_index)
        self.report({"INFO"}, f"Opening {target_abspath}")

        return {"FINISHED"}


class DATA_OT_find_missing(bpy.types.Operator):
    '''Open a file browser instance to find missing Linked Libraries'''

    bl_idname = "data.find_missing"
    bl_label = "Find missing Linked Libraries"
    bl_description = "Open a file browser instance to find missing Linked Libraries"

    directory: bpy.props.StringProperty(subtype="DIR_PATH")

    def execute(self, context):
        bpy.ops.file.find_missing_files(directory=self.directory)
        bpy.ops.data.reload_all_linked("EXEC_DEFAULT")
        return {"FINISHED"}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


# PANELS

class LINKS_MANAGER_PT_panel(bpy.types.Panel):
    bl_label = "Links Manager"
    bl_idname = "LINKS_MANAGER_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Links Manager"

    def draw(self, context):
        layout = self.layout

        linked_libs = get_linked_libraries()

        # Check if there are linked libraries in the scene
        if len(linked_libs) > 0:

            # Draw the Refresh All Libraries labels and operators
            if len(linked_libs) > 1:
                row = layout.row()
                row.label(text=f"{len(linked_libs)} Linked Libraries")
                row.operator("data.reload_all_linked", icon="FILE_REFRESH", text="Reload All")

                self.layout.separator()

            # Draw a list of Linked Libraries labels and operators
            counter = 0
            for lib in linked_libs:
                row = layout.row()

                row.label(text=f"{lib.name}", icon= "LIBRARY_DATA_BROKEN" if lib.is_missing else "LINKED")

                # Disable the Refresh column if the library is missing
                col = row.column()
                col.enabled = not lib.is_missing

                refresh_op = col.operator("data.reload_linked", icon="FILE_REFRESH", text="")
                refresh_op.target_lib_index = counter

                delete_op = row.operator("data.delete_linked", icon="TRASH", text="")
                delete_op.target_lib_index = counter

                row = layout.row()
                row.label(text=f"{bpy.path.abspath(lib.filepath)}")

                # If the library is missing, replace open file with find missing file operator button
                if lib.is_missing:
                    row.operator("data.find_missing", icon="ZOOM_ALL", text="")
                else:
                    open_op = row.operator("data.open_linked", icon="FILE_BLEND", text="")
                    open_op.target_lib_index = counter

                self.layout.separator()

                counter += 1
        else:
            row = layout.row()
            row.label(text="No linked libraries found")


# (UN)REGISTER

classes = [
            LINKS_MANAGER_PT_panel,
            DATA_OT_reload_all_linked,
            DATA_OT_reload_linked,
            DATA_OT_open_linked,
            DATA_OT_delete_linked,
            DATA_OT_find_missing,
            ]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
