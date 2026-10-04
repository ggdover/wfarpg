class_name GroundDetail
extends RefCounted
## The ground's small details baked into tiling textures, for its "Baked" level (shaders/ground_baked.gdshader): the
## same stones, grit, fallen leaves and grain that High works out for every pixel, worked out once, at startup, by
## shaders/detail_bake.gdshader, and read from the textures after that.

const SIZE := 1024  ## pixels across each texture: about 4 mm a pixel on the 4 m tiles, 1 cm on the 10 m one
const LAYERS := ["detail_small", "detail_big", "detail_flat", "detail_leaves"]  ## the ground shader's names for them


## Render each layer once into a viewport under parent, and hand it to done(name, texture) as a mipmapped texture.
## Takes a frame a layer.
static func bake(parent: Node, done: Callable) -> void:
	var vp := SubViewport.new()
	vp.size = Vector2i(SIZE, SIZE)
	vp.transparent_bg = true  # keeps the alpha the layers store
	vp.disable_3d = true
	vp.render_target_update_mode = SubViewport.UPDATE_DISABLED
	var rect := ColorRect.new()
	rect.size = Vector2(SIZE, SIZE)
	var mat := ShaderMaterial.new()
	mat.shader = load("res://shaders/detail_bake.gdshader")
	rect.material = mat
	vp.add_child(rect)
	parent.add_child(vp)
	for i in LAYERS.size():
		mat.set_shader_parameter("layer", i)
		vp.render_target_update_mode = SubViewport.UPDATE_ONCE
		await RenderingServer.frame_post_draw
		var img := vp.get_texture().get_image()
		img.generate_mipmaps()
		done.call(LAYERS[i], ImageTexture.create_from_image(img))
	vp.queue_free()
