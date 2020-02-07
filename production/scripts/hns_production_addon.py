bl_info = {
    "name": "honey nut studios production tools",
    "blender": (2, 80, 0),
    "category": "Production"
}

import bpy


class PlayblastPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__
    
    # Prevents setting the scale to values that would cause the video height or width to be odd numbers
    # (a height or width that isn't divisible by 2 causes errors when exporting).
    def scale_update(self, context):
        while (self.playblast_scale * 1920 / 100) % 2 != 0 or (self.playblast_scale * 1080 / 100) % 2 != 0:
            self.playblast_scale += 1
    
    playblast_scale: bpy.props.IntProperty(
        name="Playblast scale %",
        subtype='PERCENTAGE',
        default=50,
        min=5,
        max=100,
        update=scale_update
    )
    
    playblast_shade_solid: bpy.props.BoolProperty(
        name="Use solid shading",
        default=False
    )
    
    playblast_show_frames: bpy.props.BoolProperty(
        name="Show frame numbers",
        default=False
    )
    
    def draw(self, context):
        layout = self.layout

        box = layout.box()
        box.label(text="Playblast options:")
        
        row = box.row()
        row.label(text="Scale (default: 50%)")
        row.prop(self, "playblast_scale", text="")
        
        row = box.row()
        row.prop(self, 'playblast_shade_solid', text="Use solid shading (less pretty but faster)")
        
        row = box.row()
        row.prop(self, 'playblast_show_frames')
        
    
#####################       Playblast Operator       #####################

class ANIM_OT_playblast(bpy.types.Operator):
    """Playblasts (viewport renders) the scene with predefined settings"""
     
    # In case we ever need to playblast manually, here's a reference of everything the script does:
    # - Hides overlays
    # - Sets viewport shading to LookDev (or Workbench/Solid if set in playblast options)
    # - Aligns view with the render camera (View -> Cameras -> Active Camera)
    # - Sets these render settings:
    #       Output tab > Dimensions > Resolution % = 50% (or whatever is selected in playblast options)
    #                    Output > Render path = //[filename]_playblast.mp4
    #                             File format = FFmpeg video
    #                             Encoding > Container = MPEG-4
    #                             Video > Video Codec = H.264
    #                                     Output quality = Medium quality
    #                    Metadata > Burn Into Image
    #                               (shows a note with the shot name, and optionally the frame number;
    #                                disables all the other overlays that are shown by default)
    # 
    # These settings should already be set in the shot file:
    #       Scene tab > Scene > Camera = render_cam
    #       Output tab > Dimensions > Resolution X/Y = 1920px by 1080px
    #                                 Aspect X/Y = 1.0
    #                                 Frame Start/End = scene start/end, Step = 1
    #                                 Frame Rate = 24 fps 
    
    bl_idname = "anim.playblast"
    bl_label = "Playblast"
    
    def execute(self, context):
        addon_prefs = context.preferences.addons[__name__].preferences
        render = context.scene.render
        
        base_font_size = 60
        
        # save scene settings
        old_frame = context.scene.frame_current
        old_resolution = render.resolution_percentage
        old_file_format = render.image_settings.file_format
        old_codec = render.ffmpeg.codec
        old_format = render.ffmpeg.format
        old_constant_rate_factor = render.ffmpeg.constant_rate_factor
        old_filepath = render.filepath
        
        # set playblast render settings
        render.resolution_percentage = addon_prefs.playblast_scale
        render.image_settings.file_format = 'FFMPEG'
        render.ffmpeg.codec = 'H264'
        render.ffmpeg.format = 'MPEG4'
        render.ffmpeg.constant_rate_factor = 'MEDIUM'
        
        shot_name = bpy.path.basename(bpy.data.filepath).replace(".blend", "")
        render.filepath = "//" + shot_name + "_playblast.mp4"
        
        # set stamp (text overlay) settings - don't bother restoring these settings
        render.use_stamp = True
        render.stamp_font_size = base_font_size * addon_prefs.playblast_scale / 100
        
        render.use_stamp_frame = addon_prefs.playblast_show_frames
        render.use_stamp_note = True
        render.stamp_note_text = shot_name.replace("_", " ").title()
        
        render.use_stamp_camera = False
        render.use_stamp_date = False
        render.use_stamp_filename = False
        render.use_stamp_memory = False
        render.use_stamp_render_time = False
        render.use_stamp_scene = False
        render.use_stamp_time = False
        
        # a bit hacky, but this opens a new temporary window
        context.scene.render.display_mode = 'WINDOW'
        bpy.ops.render.view_show('INVOKE_DEFAULT')
        
        area = context.window_manager.windows[-1].screen.areas[0]  
        area.type = 'VIEW_3D'
        view3d_space = next(s for s in area.spaces if s.type == 'VIEW_3D')
        view3d_space.overlay.show_overlays = False
        view3d_space.shading.type = 'SOLID' if addon_prefs.playblast_shade_solid else 'MATERIAL'
        # I think this should be set by default, but just in case?
        view3d_space.camera = context.scene.camera

        context_override = {}
        context_override["window"] = context.window_manager.windows[-1]
        context_override["area"] = area
        context_override["region"] = next(r for r in area.regions if r.type == 'WINDOW')
        
        # assumes the new 3D View is always a non-active-camera view by default
        bpy.ops.view3d.view_camera(context_override)
        
        bpy.ops.render.opengl(context_override, animation=True)
        bpy.ops.wm.window_close(context_override)
        
        # restore scene settings
        context.scene.frame_set(old_frame)
        render.resolution_percentage = old_resolution
        render.image_settings.file_format = old_file_format
        render.ffmpeg.codec = old_codec
        render.ffmpeg.format = old_format
        render.ffmpeg.constant_rate_factor = old_constant_rate_factor
        render.filepath = old_filepath
        
        return {'FINISHED'}
        
        
def pb_menu_func(self, context):
    self.layout.separator()
    self.layout.operator(ANIM_OT_playblast.bl_idname)


#####################       Rig Operators       #####################

class ARMATURE_OT_fk_ik_switch(bpy.types.Operator):
    """Switches the selected limb to IK or FK mode.

      (Probably stable, but still use with caution)"""
        
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
    """Selects all controls on the rig except the TopCon."""
    
    bl_idname = "pose.select_all_anims"
    bl_label = "Select All Anims"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    
    @classmethod
    def poll(cls, context):
        return (context.active_object.type == 'ARMATURE'
            and bpy.ops.pose.select_all.poll())
        
    def execute(self, context):
        bpy.ops.pose.select_all(action='SELECT')
        context.active_object.data.bones["TopCon"].select = False
        return {'FINISHED'}
    
    
class ARMATURE_OT_key_whole_character(bpy.types.Operator):
    """Keys all controls on the rig except the TopCon."""
        
    bl_idname = "armature.key_whole_character"
    bl_label = "Key Whole Character"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return context.mode == 'POSE'
    
    def execute(self, context):
        #context.scene.keying_sets_all.active = context.scene.keying_sets_all['Whole Character']
        #bpy.ops.anim.keyframe_insert(type='WholeCharacter')
        bpy.ops.pose.select_all_anims()
        bpy.ops.anim.keyframe_insert_by_name(type="LocRotScale")
        return {'FINISHED'}
        
        
#####################       Rig Panels       #####################

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
        
        op = layout.operator("pose.group_switch_and_select", text="Leaf")
        op.group = "Leaf"
        
        op = layout.operator("pose.group_switch_and_select", text="Skirt")
        op.group = "Skirt"
        
        # doesn't select hidden anims
        op = layout.operator("pose.select_all_anims", text="All (Visible) Anims")

    
def register():
    bpy.utils.register_class(PlayblastPreferences)
    bpy.utils.register_class(ANIM_OT_playblast)
    bpy.types.TOPBAR_MT_render.append(pb_menu_func)
    
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
    
    bpy.types.TOPBAR_MT_render.remove(pb_menu_func)
    bpy.utils.unregister_class(ANIM_OT_playblast)
    bpy.utils.unregister_class(PlayblastPreferences)


if __name__ == "__main__":
    register()