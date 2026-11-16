shader_type spatial;
// Pigeons and gulls (scripts/birds.gd). One MultiMesh per species; the wings, head and legs are animated here from
// INSTANCE_CUSTOM:  x = wing flap angle (rad, + = up), y = wing fold (0 spread .. 1 folded on the back),
//                   z = head pitch (rad, - = peck down), w = walk phase (0..2pi, 8 = legs tucked) + 10 * variant.
// Vertex colour alpha: 1 feathers, 0.75 iridescent neck, 0 bare parts (beak, legs, eyes).
// Mesh UV2.x tags the part: 0 body, 1 left wing, 2 right wing, 3 head, 4 left leg, 5 right leg;
// UV2.y = fraction of the wing span; UV = (span, chord) on the wings for the feather pattern.
render_mode cull_disabled, diffuse_burley, specular_schlick_ggx;

uniform bool gull = false;
uniform vec3 shoulder = vec3(0.045, 0.16, -0.04);
uniform vec3 neck = vec3(0.0, 0.17, -0.09);
uniform vec3 hip = vec3(0.025, 0.07, 0.0);

varying float v_part;
varying vec2 v_wing;
varying float v_variant;
varying vec3 v_wp;
varying vec3 v_wn;

vec3 rot_x(vec3 p, float a) { float c = cos(a), s = sin(a); return vec3(p.x, p.y * c - p.z * s, p.y * s + p.z * c); }
vec3 rot_y(vec3 p, float a) { float c = cos(a), s = sin(a); return vec3(p.x * c + p.z * s, p.y, -p.x * s + p.z * c); }
vec3 rot_z(vec3 p, float a) { float c = cos(a), s = sin(a); return vec3(p.x * c - p.y * s, p.x * s + p.y * c, p.z); }

void vertex() {
	float part = floor(UV2.x + 0.5);
	vec4 cd = INSTANCE_CUSTOM;
	float walk = mod(cd.w, 10.0);
	v_variant = floor(cd.w / 10.0);
	v_part = part;
	v_wing = UV;
	vec3 p = VERTEX;
	vec3 n = NORMAL;
	if (part == 1.0 || part == 2.0) {
		float sd = part == 2.0 ? 1.0 : -1.0;
		vec3 piv = vec3(sd * shoulder.x, shoulder.y, shoulder.z);
		vec3 q = p - piv;
		float fold = cd.y;
		// fold: sweep the wing back along the body, then roll its chord down along the flank
		q = rot_y(q, -sd * fold * 1.5);
		n = rot_y(n, -sd * fold * 1.5);
		q = rot_z(q, sd * fold * 1.2);
		n = rot_z(n, sd * fold * 1.2);
		q.y -= fold * 0.012 * UV2.y;
		// flap: the hand bends further than the arm
		float a = sd * cd.x * (1.0 + 0.45 * UV2.y);
		q = rot_z(q, a);
		n = rot_z(n, a);
		p = piv + q;
	} else if (part == 3.0) {
		float bob = sin(walk * 2.0) * 0.018;
		vec3 q = rot_x(p - neck, cd.z);
		n = rot_x(n, cd.z);
		p = neck + q + vec3(0.0, 0.0, -bob);
	} else if (part >= 4.0) {
		float sd = part == 5.0 ? 1.0 : -1.0;
		vec3 piv = vec3(sd * hip.x, hip.y, hip.z);
		// walk phase above 6.5 means "in flight": the legs are tucked back under the tail
		float a = walk > 6.5 ? -1.3 : sin(walk + (sd > 0.0 ? 3.14159 : 0.0)) * 0.55;
		p = piv + rot_x(p - piv, a);
		n = rot_x(n, a);
	}
	VERTEX = p;
	NORMAL = n;
	v_wp = (MODEL_MATRIX * vec4(p, 1.0)).xyz;
	v_wn = (MODEL_MATRIX * vec4(n, 0.0)).xyz;      // the top side of the wing, before any back-face flip
}

void fragment() {
	vec3 c = COLOR.rgb;
	float part = floor(v_part + 0.5);
	bool skin = COLOR.a < 0.5;          // beak, legs, eyes keep their colour
	if (part == 1.0 || part == 2.0) {
		float s = v_wing.x, ch = v_wing.y;
		if (gull) {
			// pale grey on top, white underneath (that is what you see from the bridge), black tips
			bool under = dot(CAMERA_POSITION_WORLD - v_wp, v_wn) < 0.0;
			c = under ? vec3(0.95, 0.95, 0.96) : vec3(0.8, 0.83, 0.87);
			float tip = smoothstep(0.74, 0.8, s);
			c = mix(c, vec3(0.06, 0.06, 0.07), tip);
			float mirror = step(0.9, s) * step(0.45, ch) * step(ch, 0.75);
			c = mix(c, vec3(0.92), mirror);
			c = mix(c, vec3(0.94), smoothstep(0.85, 0.97, ch) * (1.0 - tip));   // white trailing edge
		} else {
			c = vec3(0.6, 0.63, 0.68);
			float bars = (step(0.42, ch) * step(ch, 0.52) + step(0.62, ch) * step(ch, 0.72)) * step(s, 0.5) * step(0.12, s);
			c = mix(c, vec3(0.13, 0.13, 0.15), bars);
			c = mix(c, vec3(0.3, 0.31, 0.35), smoothstep(0.6, 0.72, s));
		}
	}
	if (!gull && !skin) {
		if (v_variant == 1.0) {
			c *= vec3(0.55, 0.55, 0.6);                                 // dark checker
		} else if (v_variant == 2.0) {
			c = mix(c, vec3(0.92, 0.91, 0.88), 0.7);                     // pale
		} else if (v_variant == 3.0) {
			c = mix(c, vec3(0.5, 0.36, 0.27), 0.55);                     // red-brown
		}
	}
	c = pow(c, vec3(2.2));            // colours above are sRGB
	ALBEDO = c;
	ROUGHNESS = skin ? 0.5 : 0.85;
	SPECULAR = 0.3;
	if (gull) {
		EMISSION = c * 0.22;          // sunlit white plumage still reads white against the bright sky
	}
	// iridescent neck of the pigeons
	if (!gull && COLOR.a > 0.6 && COLOR.a < 0.9) {
		float f = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 2.0);
		ALBEDO = mix(c, vec3(0.17, 0.05, 0.2), f * 0.6) + vec3(0.0, 0.03, 0.015) * (1.0 - f);
	}
}
