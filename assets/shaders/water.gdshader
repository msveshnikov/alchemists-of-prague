// Vltava: procedural ripples (no textures, no screen reads -> works on the Compatibility renderer for web/Android).
shader_type spatial;
render_mode cull_disabled, specular_schlick_ggx;

uniform vec3 deep : source_color = vec3(0.045, 0.11, 0.12);
uniform vec3 shallow : source_color = vec3(0.13, 0.24, 0.23);
uniform float wave_strength = 0.55;

varying vec3 wpos;

float waves(vec2 p, float t) {
	float h = sin(p.x * 0.31 + t * 0.8) * 0.5;
	h += sin(p.y * 0.23 - t * 0.6 + p.x * 0.07) * 0.5;
	h += sin((p.x + p.y) * 0.9 + t * 1.6) * 0.18;
	h += sin((p.x * 1.7 - p.y * 1.3) + t * 2.3) * 0.1;
	return h;
}

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec2 p = wpos.xz + vec2(0.0, TIME * 0.6);   // the river flows north (-Z)
	float e = 0.15;
	float dx = waves(p + vec2(e, 0.0), TIME) - waves(p - vec2(e, 0.0), TIME);
	float dz = waves(p + vec2(0.0, e), TIME) - waves(p - vec2(0.0, e), TIME);
	vec3 n = normalize(vec3(-dx * wave_strength, 1.0, -dz * wave_strength));
	NORMAL = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);
	float m = 0.5 + 0.5 * sin(wpos.x * 0.02 + wpos.z * 0.013);
	ALBEDO = mix(deep, shallow, 0.25 + 0.35 * m);
	ROUGHNESS = 0.06;
	METALLIC = 0.0;
	SPECULAR = 0.65;
}
