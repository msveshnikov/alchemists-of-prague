shader_type spatial;
// World-space paving (Old Town cobbles, Charles Bridge setts), textures from tools/make_paving.py.
// UVs come from the world X/Z position, so neighbouring ground tiles join without seams. Parallax occlusion
// mapping gives the stones real depth near the camera; a low-frequency macro map adds dirt, hue drift and
// rain puddles that fill the joints and dips, which hides the texture repeat.
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;

uniform sampler2D albedo_h : source_color, filter_linear_mipmap_anisotropic, repeat_enable;   // RGB albedo, A height
uniform sampler2D normal_tex : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D macro_tex : filter_linear_mipmap, repeat_enable;
uniform float tile_m = 4.0;           // metres per texture repeat
uniform float depth_m = 0.05;         // joint depth, metres
uniform vec3 tint : source_color = vec3(1.0);
uniform float puddles = 0.45;         // 0 = dry, 1 = after heavy rain
uniform float dirt = 0.5;
uniform float saturation = 0.55;
uniform float brightness = 0.7;
uniform float pom_far = 18.0;         // parallax fades out by this distance

varying vec3 wpos;
varying vec3 wnrm;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wnrm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

void fragment() {
	vec3 N0 = normalize(wnrm);
	vec3 T = vec3(1.0, 0.0, 0.0) - N0 * N0.x;
	T = dot(T, T) < 0.01 ? vec3(0.0, 0.0, 1.0) : normalize(T);
	vec3 B = normalize(cross(T, N0));
	vec2 uv = wpos.xz / tile_m;
	vec3 to_cam = CAMERA_POSITION_WORLD - wpos;
	float dist = length(to_cam);
	vec3 V = to_cam / dist;
	vec2 gx = dFdx(uv);
	vec2 gy = dFdy(uv);

	float fade = 1.0 - smoothstep(pom_far * 0.55, pom_far, dist);
	if (fade > 0.01) {
		vec3 vt = vec3(dot(V, T), dot(V, B), dot(V, N0));
#if CURRENT_RENDERER == RENDERER_COMPATIBILITY || CURRENT_RENDERER == RENDERER_MOBILE
		float steps = mix(8.0, 4.0, vt.z);
#else
		float steps = mix(16.0, 6.0, vt.z);
#endif
		float layer = 1.0 / steps;
		vec2 P = vt.xy / max(vt.z, 0.2) * (depth_m / tile_m) * fade;
		vec2 duv = P * layer;
		float cur = 0.0;
		vec2 cuv = uv;
		float d = 1.0 - textureGrad(albedo_h, cuv, gx, gy).a;
		for (int i = 0; i < 32; i++) {
			if (cur >= d || float(i) >= steps) {
				break;
			}
			cuv -= duv;
			d = 1.0 - textureGrad(albedo_h, cuv, gx, gy).a;
			cur += layer;
		}
		vec2 puv = cuv + duv;
		float after = d - cur;
		float before = (1.0 - textureGrad(albedo_h, puv, gx, gy).a) - cur + layer;
		float w = after / (after - before);
		uv = mix(cuv, puv, clamp(w, 0.0, 1.0));
	}

	vec4 ah = textureGrad(albedo_h, uv, gx, gy);
	float h = ah.a;
	vec2 nxy = textureGrad(normal_tex, uv, gx, gy).rg * 2.0 - 1.0;
	float far_k = smoothstep(12.0, 55.0, dist);   // calm the relief far away: no sky glitter in the shadows
	nxy *= 1.0 - 0.65 * far_k;
	float nz = sqrt(max(1.0 - dot(nxy, nxy), 0.0));

	vec2 mp = wpos.xz;
	vec3 m1 = texture(macro_tex, mp / 61.0).rgb;
	vec3 m2 = texture(macro_tex, mp / 13.0 + vec2(0.37, 0.71)).rgb;
	// puddles: water fills the joints and dips where the macro map says so; elsewhere the joints are just damp
	float pool = smoothstep(0.8 - 0.25 * puddles, 0.88 - 0.25 * puddles, m1.g * 0.8 + m2.g * 0.3) * step(0.01, puddles);
	float level = pool * 1.15;          // the middle of a puddle drowns whole stones: one calm mirror, not glitter
	float water = smoothstep(level, level - 0.06, h) * step(0.001, level);
#if CURRENT_RENDERER == RENDERER_COMPATIBILITY || CURRENT_RENDERER == RENDERER_MOBILE
	water *= 0.35;                      // no screen-space tricks there: keep the puddles matt
#endif
	float damp = clamp(water + pool * 0.6 + (1.0 - h) * 0.25 * puddles, 0.0, 1.0);

	vec3 col = ah.rgb;
	float lum = dot(col, vec3(0.3, 0.55, 0.15));
	col = mix(vec3(lum), col, saturation) * tint * brightness;
	vec3 grime = vec3(0.32, 0.27, 0.2);
	col = mix(col, col * grime * 2.2, smoothstep(0.4, 0.8, m1.r) * dirt);
	col = mix(col, col * grime * 2.6, (1.0 - smoothstep(0.05, 0.35, h)) * dirt);   // muck in the joints
	col *= 0.8 + 0.35 * m2.b;
	col = mix(col, col * vec3(1.04, 0.98, 0.9), smoothstep(0.3, 0.7, m1.b) * 0.6);
	col *= mix(1.0, 0.5, damp);
	col *= mix(1.0, 0.6, water);
	ALBEDO = col;

	vec3 nw = normalize(T * nxy.x + B * nxy.y + N0 * nz);
	nw = normalize(mix(nw, N0, water * 0.92));
	NORMAL = normalize((VIEW_MATRIX * vec4(nw, 0.0)).xyz);
	ROUGHNESS = mix(mix(0.97, 0.84, h), 0.3, max(water, damp * 0.35));
	ROUGHNESS = mix(ROUGHNESS, max(ROUGHNESS, 0.97), far_k * (1.0 - water));
	SPECULAR = mix(mix(0.25, 0.12, far_k), 0.3, water);
	AO = mix(0.55, 1.0, smoothstep(0.0, 0.55, h));
	AO_LIGHT_AFFECT = 0.35;
}
