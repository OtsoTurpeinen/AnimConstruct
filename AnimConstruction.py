bl_info = {
    "name": "Animate Construction",
    "description": "Tools to help creating construction animations. ",
    "author": "Otso Turpeinen",
    "version": (1, 0, 0),
    "blender": (2, 79, 0),
    "location": "3D View > Tools",
    "warning": "", # used for warning icon and text in addons panel
    "wiki_url": "",
    "tracker_url": "",
    "category": "Object",
}

import bpy
import math
import mathutils
import sys

#Animation construction properties.
class AnimCon_Properties(bpy.types.PropertyGroup):
    m_SortVector = bpy.props.FloatVectorProperty(name="Sort Vector", description="Vector used for sorting the objects", default=(0.0001, 0.0001, 1.0), step=3, precision=2, unit='LENGTH', size=3)
    m_Translate = bpy.props.FloatVectorProperty(name="Translate", description="Animation Translation", default=(0.0, 0.0, 1.0), step=3, precision=2, unit='LENGTH', size=3)
    m_Scale = bpy.props.FloatVectorProperty(name="Scale", description="Animation Scale", default=(1.0, 1.0, 1.0), step=3, precision=2, unit='LENGTH', size=3)
    m_Rotation = bpy.props.FloatVectorProperty(name="Rotation", description="Animation Rotation", default=(0.0, 0.0, 0.0), step=3, precision=2, unit='ROTATION', size=3)
    m_KeyfamePer = bpy.props.IntProperty(name="Keyframes", description="Keyframes per object", default=1, min=1, max=9999, soft_min=1, soft_max=9999, step=1)
    m_KeyOverlap = bpy.props.IntProperty(name="Overlap", description="Animation overlap between different objects.", default=0, min=-9999, max=9999, soft_min=-9999, soft_max=9999, step=1)

   # m_AfterTranslate = bpy.props.FloatVectorProperty(name="Move out Translate", description="Animation Translation", default=(20.0, 0.0, 0.0), step=3, precision=2, unit='LENGTH', size=3)
   # m_AfterKeyfame = bpy.props.IntProperty(name="Move out Keyframes", description="Keyframes for move out", default=0, min=0, max=9999, soft_min=0, soft_max=9999, step=1)

#Properties for origin offset tool. 
class AnimConHelp_Properties(bpy.types.PropertyGroup):
    m_Translate = bpy.props.FloatVectorProperty(name="Origin", description="Origin Translation", default=(0.0, 0.0, 1.0), step=3, precision=2, unit='LENGTH', size=3)
    
#Operator for origin offset tool.
class AnimCon_Offset_Operator(bpy.types.Operator):
    bl_idname = 'construct.offset'
    bl_label = "Animate Construction: Batch Origin Offset"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self,context):
        scene = context.scene
        mytool = scene.anim_helper_tool
        scn = bpy.context.scene
        self.setselect(bpy.context.selected_objects,False)
        self.opsOffsetChange(bpy.context.selected_objects,mytool.m_Translate)
        self.setselect(bpy.context.selected_objects,True)
        return {'FINISHED'}

    #function to (de)select objects.
    def setselect(self,ls,s):
        for obj in ls:
            obj.select = s

    def opsOffsetChange(self,ls,vec):
        #I use the cursor as helper here, so for peace of mind, I like to save the cursor position for restoration later.
        pt = bpy.context.scene.cursor_location
        bpy.ops.object.mode_set(mode = 'OBJECT')
        for obj in ls:
            bpy.context.scene.objects.active = obj
            obj.select = True
            avec = obj.location
            bvec = (vec[0]+avec[0],vec[1]+avec[1],vec[2]+avec[2])
            bpy.context.scene.cursor_location = bvec
            bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
            obj.select = False
        bpy.context.scene.cursor_location = pt 


#Operator for construction animation tool.
class AnimCon_Operator(bpy.types.Operator):
    bl_idname = 'construct.anim'
    bl_label = "Animate Construction"
    bl_options = {'REGISTER', 'UNDO'}
    sortVec = {0.0,0.0,1.0}

    def execute(self,context):
        scene = context.scene
        mytool = scene.anim_construct_tool
        sorted_select = bpy.context.selected_objects
        self.sortVec = mytool.m_SortVector
        sorted_select.sort(key=self.vectorSort)
        scn = bpy.context.scene
        #Calculating length of the whole animation.
        end_frame = scn.frame_current+(len(sorted_select)+1)*(mytool.m_KeyfamePer-mytool.m_KeyOverlap)+mytool.m_KeyfamePer
        #I don't want to change the end_frame if this is not the last animation to finish.
        if (scn.frame_end < end_frame+1):
            scn.frame_end = end_frame+1
        self.setselect(sorted_select,False)
        #decided to pass on the whole tool because there are so many parameters.
        self.opsGenerateAnimation(sorted_select,scn.frame_current,end_frame,mytool)
        self.setselect(sorted_select,True)
        return {'FINISHED'}

    #Sorting by vector. 
    def vectorSort(self,obj):
        return obj.location[0]*self.sortVec[0]+obj.location[1]*self.sortVec[1]+obj.location[2]*self.sortVec[2]


    def setselect(self,ls,s):
        for obj in ls:
            obj.select = s


    #Generating the animation here.
    def opsGenerateAnimation(self,ls,start_frame,end_frame,tool):
        n = 1
        alpo = tool.m_KeyfamePer
        ao = tool.m_KeyOverlap
        #outkey = tool.m_AfterKeyfame
        vec = tool.m_Translate
        rot = tool.m_Rotation
        scl = tool.m_Scale
        btra = (abs(vec[0]) > 0.00000 or abs(vec[1]) > 0.00000 or abs(vec[2]) > 0.00000)
        brot = (abs(rot[0]) > 0.00000 or abs(rot[1]) > 0.00000 or abs(rot[2]) > 0.00000)
        bscl = (abs(scl[0]) > 0.00000 or abs(scl[1]) > 0.00000 or abs(scl[2]) > 0.00000)
        for obj in ls:
            #we need to select the object to use the translate & keyframe ops.
            bpy.context.scene.objects.active = obj
            obj.select = True
            
            #make sure we are in object mode
            ovec = (vec[0]*-1,vec[1]*-1,vec[2]*-1)
            orot = (rot[0]*-1,rot[1]*-1,rot[2]*-1)
            oscl = (scl[0]*-1,scl[1]*-1,scl[2]*-1)
            #oscl = (obj.scale.x,obj.scale.y,obj.scale.z)
            bpy.ops.object.mode_set(mode = 'OBJECT')

            #do start frames
            correct_frame = start_frame+max(n*(alpo-ao),0)
            #bpy.context.scene.frame_set(correct_frame)
            if (btra):
                obj.location.x += vec[0]
                obj.location.y += vec[1]
                obj.location.z += vec[2]
                obj.keyframe_insert(data_path='location', frame=correct_frame)
            if (brot):
                obj.rotation_euler.x += rot[0]
                obj.rotation_euler.y += rot[1]
                obj.rotation_euler.z += rot[2]
                obj.keyframe_insert(data_path='rotation_euler', frame=correct_frame)
            if (bscl):
                obj.scale.x += scl[0]
                obj.scale.y += scl[1]
                obj.scale.z += scl[2]
                obj.keyframe_insert(data_path='scale', frame=correct_frame)
            #bpy.ops.transform.translate(value=vec)
            #bpy.ops.anim.keyframe_insert_menu(type='Location')

            n += 1
            correct_frame = correct_frame+alpo

            #do end frame
            #bpy.context.scene.frame_set(min(end_frame,correct_frame))
            #bpy.ops.transform.translate(value=ovec)
            #bpy.ops.anim.keyframe_insert_menu(type='Location')
            if (btra):
                obj.location.x += ovec[0]
                obj.location.y += ovec[1]
                obj.location.z += ovec[2]
                obj.keyframe_insert(data_path='location', frame=correct_frame)
                obj.keyframe_insert(data_path='location', frame=end_frame+1)
            if (brot):
                obj.rotation_euler.x += orot[0]
                obj.rotation_euler.y += orot[1]
                obj.rotation_euler.z += orot[2]
                obj.keyframe_insert(data_path='rotation_euler', frame=correct_frame)
                obj.keyframe_insert(data_path='rotation_euler', frame=end_frame+1)
            if (bscl):
                obj.scale.x = oscl[0]
                obj.scale.y = oscl[1]
                obj.scale.z = oscl[2]
                obj.keyframe_insert(data_path='scale', frame=correct_frame)
                obj.keyframe_insert(data_path='scale', frame=end_frame+1)
            
            #do end freeze frame

            #do end freeze frame
            #bpy.context.scene.frame_set(end_frame+1)
            #bpy.ops.anim.keyframe_insert_menu(type='Location')

            #do end out frame
            #if (outkey > 0):
            #    bpy.context.scene.frame_set(end_frame+1+outkey)
            #    bpy.ops.transform.translate(value=outvec)
            #    bpy.ops.anim.keyframe_insert_menu(type='Location')
            #Deselect and count up
            obj.select = False
        
        #bpy.context.scene.frame_set(start_frame)
    

class AnimCon_Panel(bpy.types.Panel):
    bl_idname = "construct.animpanel"
    bl_label = "Animate Construction"
    bl_space_type = "VIEW_3D"   
    bl_region_type = "TOOLS"    
    bl_category = "Automation"
    bl_context = "objectmode"   

    @classmethod
    def poll(self,context):
        return context.object is not None

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        mytool = scene.anim_construct_tool
        #nrow.prop(mytool, "m_ReverseSort") 
        ncol = layout.column()
        ncol.prop(mytool, "m_SortVector")
        ncol.prop(mytool, "m_Translate")
        ncol.prop(mytool, "m_Scale")
        ncol.prop(mytool, "m_Rotation")
        ncol.prop(mytool, "m_KeyfamePer")
        ncol.prop(mytool, "m_KeyOverlap")
        #ncol.prop(mytool, "m_AfterTranslate")
        #ncol.prop(mytool, "m_AfterKeyfame")
        layout.operator(AnimCon_Operator.bl_idname,text="Generate Animation")

class AnimConOffset_Panel(bpy.types.Panel):
    bl_idname = "construct.animhelppanel"
    bl_label = "Offset Tools"
    bl_space_type = "VIEW_3D"   
    bl_region_type = "TOOLS"    
    bl_category = "Automation"
    bl_context = "objectmode"   

    @classmethod
    def poll(self,context):
        return context.object is not None

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        myhelper = scene.anim_helper_tool
        #nrow.prop(mytool, "m_ReverseSort") 
        ncol = layout.column()
        ncol.prop(myhelper, "m_Translate")
        layout.operator(AnimCon_Offset_Operator.bl_idname,text="Batch Origin Offset")

def register():
    bpy.utils.register_module(__name__)
    bpy.types.Scene.anim_construct_tool = bpy.props.PointerProperty(type=AnimCon_Properties)
    bpy.types.Scene.anim_helper_tool = bpy.props.PointerProperty(type=AnimConHelp_Properties)

def unregister():
    bpy.utils.unregister_module(__name__)
    del bpy.types.Scene.anim_construct_tool
    del bpy.types.Scene.anim_helper_tool

if __name__ == "__main__":
    register()