bl_info = {
    "name": "honey nut studios production tools",
    "blender": (2, 80, 0),
    "category": "Production"
}

import bpy


#####################       Playblast Operator       #####################

class ANIM_OT_playblast(bpy.types.Operator):
    """Playblasts (viewport renders) the scene with predefined settings"""
        
    bl_idname = "anim.playblast"
    bl_label = "Playblast"
    
    def execute(self, context):
        # still need to restore old render settings, or make a copy
        # (of the scene? or just render settings?) to modify & pass in
        
        render = context.scene.render
        render.resolution_percentage = 50
        render.image_settings.file_format = 'FFMPEG'
        render.ffmpeg.codec = 'H264'
        render.ffmpeg.format = 'MPEG4'
        
        filename = bpy.path.basename(bpy.data.filepath).replace(".blend", "")
        render.filepath = "//" + filename + "_playblast.mp4"
        
        # a bit hacky, but this opens a new temporary window
        context.scene.render.display_mode = 'WINDOW'
        bpy.ops.render.view_show('INVOKE_DEFAULT')

        area = context.window_manager.windows[-1].screen.areas[0]  
        area.type = 'VIEW_3D'
        
        area.spaces[0].overlay.show_overlays = False
        # I think this should be set by default, but just in case?
        area.spaces[0].camera = context.scene.camera

        context_override = {}  # context.copy()
        context_override["window"] = context.window_manager.windows[-1];
        context_override["area"] = area;
        context_override["region"] = [r for r in area.regions if r.type == 'WINDOW'][0]
        
        # assumes 3D View is always a non-active-camera view by default,
        # because there's no way to check the current state for this toggle function :\
        bpy.ops.view3d.view_camera(context_override)
        
        # do any of the operators besides view_camera need to have the context overridden?
        # seems to work because the new render window is always active anyway; OK to assume it always will be...?
        bpy.ops.view3d.toggle_shading(type='MATERIAL')
                
        bpy.ops.render.opengl(animation=True)
        bpy.ops.wm.window_close()
        return {'FINISHED'}


#####################       Rig Operators       #####################

class ARMATURE_OT_fk_ik_switch(bpy.types.Operator):
    """Switches the selected limb to IK or FK mode.

      (May or may not be stable?? Use with caution)"""
        
    bl_idname = "armature.fk_ik_switch"
    bl_label = "FK/IK Switch Operator"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    
    mode: bpy.props.EnumProperty(items=
        (('FK', "FK", "", 0), ('IK', "IK", "", 1)))
    switch: bpy.props.EnumProperty(items=(
        ('ARM_L', "Left Arm", ""),('ARM_R', "Right Arm", ""),
        ('LEG_L', "Left Leg", ""),('LEG_R', "Right Leg", "")))
    
    def execute(self, context):
        switch_bones = {
                'ARM_L': context.active_object.pose.bones["ArmIKSwitch.L"],
                'ARM_R': context.active_object.pose.bones["ArmIKSwitch.R"],
                'LEG_L': context.active_object.pose.bones["LegIKSwitch.L"],
                'LEG_R': context.active_object.pose.bones["LegIKSwitch.R"]}
        
        if self.mode == 'FK':
            switch_bones[self.switch]["ik_switch"] = 0.0
            switch_bones[self.switch].keyframe_insert(data_path='["ik_switch"]')
        else:
            switch_bones[self.switch]["ik_switch"] = 1.0
            switch_bones[self.switch].keyframe_insert(data_path='["ik_switch"]')
            
        # hacky way of getting the viewport to update
        bpy.ops.object.mode_set(toggle=True)
        bpy.ops.object.mode_set(toggle=True)
        return {'FINISHED'}


class POSE_OT_group_switch_and_select(bpy.types.Operator):
    """Makes the given bone group active and selects all its bones.
        
       Does nothing if group doesn't match the name of a bone group
       on the active object."""
    
    bl_idname = "pose.group_switch_and_select"
    bl_label = "Switch and Select Bone Group"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    
    group: bpy.props.StringProperty()
    
    @classmethod
    def poll(cls, context):
        return (context.active_object.type == 'ARMATURE'
            and bpy.ops.pose.group_select.poll())
        
    def execute(self, context):
        bone_groups = context.active_object.pose.bone_groups
        
        if self.group in bone_groups:
            bone_groups.active = bone_groups[self.group]
            bpy.ops.pose.group_select()
        return {'FINISHED'}
    
    
class POSE_OT_select_all_anims(bpy.types.Operator):
    """Selects all anims on the rig, including hidden FK/IK controls.
        
       (Does not select the TopCon.)
       (Also does not actually work)"""
    
    bl_idname = "pose.select_all_anims"
    bl_label = "Select All Anims"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    
    @classmethod
    def poll(cls, context):
        return (context.active_object.type == 'ARMATURE'
            and bpy.ops.pose.group_select.poll())
        
    def execute(self, context):
        bone_groups = context.active_object.pose.bone_groups
        anim_groups = ["Anims", "FK_Anims", "IK_Anims", "Skirt", "Switches"]
        
        for group in anim_groups:
            bone_groups.active = bone_groups[group]
            bpy.ops.pose.group_select()
        return {'FINISHED'}
    
    
class ARMATURE_OT_key_whole_character(bpy.types.Operator):
    """Keys all bones on the armature."""
        
    bl_idname = "armature.key_whole_character"
    bl_label = "Key Whole Character"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return context.mode == 'POSE'
    
    def execute(self, context):
        context.scene.keying_sets_all.active = context.scene.keying_sets_all['Whole Character']
        bpy.ops.anim.keyframe_insert(type='WholeCharacter')
        return {'FINISHED'}
        
        
#####################       Panels       #####################

class DATA_PT_twig_rig(bpy.types.Panel):
    """Creates a Rig Options panel in the armature tab of the properties editor"""
    
    bl_label = "Rig Options: Twig"
    bl_idname = "DATA_PT_twig_rig"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"
    
    @classmethod
    def poll(cls, context):
        return(context.active_object.type == 'ARMATURE'
            and context.active_object.name.startswith("Twig_proxy"))

    def draw(self, context):
        layout = self.layout
        
        
class DATA_PT_twig_rig_switches(bpy.types.Panel):
    """Creates a subpanel of the the Rig Options panel"""
    
    bl_label = "Switch Controls"
    bl_idname = "DATA_PT_twig_rig_switches"
    bl_parent_id = "DATA_PT_twig_rig"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    
    def draw(self, context):
        layout = self.layout        
        rig = context.active_object  # bpy.data.objects["Twig_proxy"]
 
        # IK/FK switches
        split = layout.split(factor=.15)

        col = split.column()
        col.label(text="FK/IK")
        col.label(text="Arm:")
        col.label(text="Leg:")
        
        col = split.column()
        col.label(text="Left:")
        row = col.row(align=True)
        op = row.operator("armature.fk_ik_switch", text="FK")
        op.switch = 'ARM_L'
        op.mode = 'FK'
        op = row.operator("armature.fk_ik_switch", text="IK")
        op.switch = 'ARM_L'
        op.mode = 'IK'
        
        row = col.row(align=True)
        op = row.operator("armature.fk_ik_switch", text="FK")
        op.switch = 'LEG_L'
        op.mode = 'FK'
        op = row.operator("armature.fk_ik_switch", text="IK")
        op.switch = 'LEG_L'
        op.mode = 'IK'
        
        # Sliders
        #col.prop(rig.pose.bones["ArmIKSwitch.L"], '["ik_switch"]', text="")
        #col.prop(rig.pose.bones["LegIKSwitch.L"], '["ik_switch"]', text="")
        
        col = split.column()
        col.label(text="Right:")
        
        row = col.row(align=True)
        op = row.operator("armature.fk_ik_switch", text="FK")
        op.switch = 'ARM_R'
        op.mode = 'FK'
        op = row.operator("armature.fk_ik_switch", text="IK")
        op.switch = 'ARM_R'
        op.mode = 'IK'
        
        row = col.row(align=True)
        op = row.operator("armature.fk_ik_switch", text="FK")
        op.switch = 'LEG_R'
        op.mode = 'FK'
        op = row.operator("armature.fk_ik_switch", text="IK")
        op.switch = 'LEG_R'
        op.mode = 'IK'
        
        # Sliders
        #col.prop(rig.pose.bones["ArmIKSwitch.R"], '["ik_switch"]', text="")
        #col.prop(rig.pose.bones["LegIKSwitch.R"], '["ik_switch"]', text="")
            
        layout.separator()
        
        # Skirt options
        layout.prop(rig.pose.bones["COG"], '["skirt_follow_influence"]',
            text="Skirt follow influence")
        layout.prop(rig.pose.bones["COG"], '["limit_skirt_collapse"]',
            text="Limit skirt collapse")
        
        # Other switches
        split = layout.split(factor = .4)
        col = split.column()
        col.label(text="Head follow body")
        col.label(text="FK hand follow body")
        col.label(text="IK knee follow foot")
        
        col = split.column()
        col.prop(rig.pose.bones["HeadControl"], '["follow_body"]', text="")
        row = col.row()
        row.prop(rig.pose.bones["Hand.FK.L"], '["follow_body"]', text="L")
        row.prop(rig.pose.bones["Hand.FK.R"], '["follow_body"]', text="R")
        row = col.row()
        row.prop(rig.pose.bones["IKKneeTarget.L"], '["follow_foot"]', text="L")
        row.prop(rig.pose.bones["IKKneeTarget.R"], '["follow_foot"]', text="R")
        
        layout.separator()
        
        
class DATA_PT_twig_rig_select(bpy.types.Panel):
    """Creates a subpanel of the the Rig Options panel"""
    
    bl_label = "Selection/Keying"
    bl_idname = "DATA_PT_twig_rig_select"
    bl_parent_id = "DATA_PT_twig_rig"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    
    def draw(self, context):
        layout = self.layout        
        rig = context.active_object  # bpy.data.objects["Twig_proxy"]
        
        op = layout.operator("armature.key_whole_character", text="Key All Anims")
        op = layout.operator("pose.transforms_clear", text="Reset Selected Anims")

        layout.label(text="Select Anims:")
        
        split = layout.split(align=True)
        op = split.operator("pose.group_switch_and_select", text="Fingers L")
        op.group = "Fingers_L"
        op = split.operator("pose.group_switch_and_select", text="Fingers R")
        op.group = "Fingers_R"
        
        op = layout.operator("pose.group_switch_and_select", text="Skirt")
        op.group = "Skirt"
        
        # doesn't select hidden anims
        op = layout.operator("pose.select_all_anims", text="All (Visible) Anims")

    
def register():
    bpy.utils.register_class(ANIM_OT_playblast)
    
    bpy.utils.register_class(ARMATURE_OT_fk_ik_switch)
    bpy.utils.register_class(POSE_OT_group_switch_and_select)
    bpy.utils.register_class(POSE_OT_select_all_anims)
    bpy.utils.register_class(ARMATURE_OT_key_whole_character)
    
    bpy.utils.register_class(DATA_PT_twig_rig)
    bpy.utils.register_class(DATA_PT_twig_rig_select)
    bpy.utils.register_class(DATA_PT_twig_rig_switches)

    
def unregister():
    bpy.utils.unregister_class(DATA_PT_twig_rig_switches)
    bpy.utils.unregister_class(DATA_PT_twig_rig_select)
    bpy.utils.unregister_class(DATA_PT_twig_rig)
    
    bpy.utils.unregister_class(ARMATURE_OT_key_whole_character)
    bpy.utils.unregister_class(POSE_OT_select_all_anims)
    bpy.utils.unregister_class(POSE_OT_group_switch_and_select)
    bpy.utils.unregister_class(ARMATURE_OT_fk_ik_switch)
    
    bpy.utils.unregister_class(ANIM_OT_playblast)


if __name__ == "__main__":
    register()