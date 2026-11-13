# 05 — Ordering art from ChatGPT in the built-in browser

Concept and reference art is ordered from ChatGPT through the **built-in browser of the Claude desktop
app** (`mcp__Claude_Browser__*` tools), using the user's own signed-in account. No API keys.
(Claude in Chrome works too if the user prefers it; the steps are the same.)

## Generate an image

1. Open `https://chatgpt.com/` (`preview_start` with `url`, or `navigate`).
   - If the page shows "Log in", ask the user to sign in themselves in the browser pane; never type a
     password. The sign-in persists for later sessions.
   - On the cookie banner pick the "essential only" option.
2. Click the "Ask ChatGPT" box, type a prompt starting with `Generate an image:` followed by the style
   block, the subject and `no text`, press Enter.
3. Wait 30–90 s (`computer` → `wait`, then a small screenshot). The page title changes to the chat name.
4. For a hard brief (a map that must keep a layout, a set of matching sheets), first ask ChatGPT to
   **write the best prompt** ("do NOT generate an image yet, reply with just the prompt"), then in the same
   chat: "Now generate the image using exactly that prompt".

## Save it

1. Ask the user before downloading (browser rules), unless the current request already asked for it.
2. On the image press the **share** icon (find: "Share generated image"), then **Download**.
   Never press "Copy link" — that creates a public link.
3. The built-in browser drops it into `%USERPROFILE%\Downloads` (or `~/Downloads`) as `<uuid>.tmp`.
   It is a complete PNG (check the signature `89 50 4E 47`). Move it into `concept/...` or
   `concept_art/...` with a meaningful name.

Things that do NOT work (don't waste time): reading the image out of the page as base64 (MBs of tokens),
`fetch`/`<img>` from chatgpt.com to `http://127.0.0.1` (CSP), `navigator.clipboard.write` (denied).

## Attach your own image to a message (reference art, a layout render)

There is no file-picker tool and `ctrl+v` from `computer` doesn't paste the OS clipboard. This works:

1. Convert the image to a JPEG ≤ ~1 MB and serve its folder with `scripts/chatgpt_upload/serve.py`
   (CORS-enabled static server on `127.0.0.1:8766`; keep the server script outside the served folder).
   The built-in browser can open localhost when Claude runs on the same machine.
2. `navigate` to `http://127.0.0.1:8766/hop.html?f=<file>.jpg`. The hop page reads the file and jumps to
   `https://chatgpt.com/robots.txt#claudefile=<name>|<data URL>`.
   **Must be robots.txt**, not the app: if the ChatGPT app itself loads with a huge URL fragment, sending
   messages later fails with `ERR_CONNECTION_CLOSED`.
3. On robots.txt run (`javascript_tool`):
   ```js
   await new Promise(r => setTimeout(r, 1500));
   localStorage.setItem('claude_file', decodeURIComponent(location.hash.slice('#claudefile='.length)));
   history.replaceState(null, '', '/robots.txt');
   ```
4. `navigate` to `https://chatgpt.com/` and run:
   ```js
   await new Promise(r => setTimeout(r, 1500));
   const raw = localStorage.getItem('claude_file'); localStorage.removeItem('claude_file');
   const name = raw.slice(0, raw.indexOf('|')), data = raw.slice(raw.indexOf('|') + 1);
   const bin = atob(data.slice(data.indexOf(',') + 1)); const u8 = new Uint8Array(bin.length);
   for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
   const file = new File([u8], name, {type: 'image/jpeg'});
   const inp = document.querySelector('input[type=file][accept="image/*"][multiple]');
   const dt = new DataTransfer(); dt.items.add(file); inp.files = dt.files;
   inp.dispatchEvent(new Event('change', {bubbles: true}));
   ```
   (`fetch(dataURL)` is blocked by CSP, hence `atob`.)
5. Wait until the thumbnail shows in the composer, then type the text and send.
6. Stop the local server afterwards.

## Making painted art match the game exactly (e.g. the in-game map)

A painted map is useless if the player marker lands in the wrong place. Recipe:

1. Render a top-down **orthographic plan** of the real level in Blender (known centre and size in
   metres). Crop it to the playable area at the aspect ChatGPT outputs (3:2 → 1536×1024) and record the
   world rectangle the crop covers (`x0, z0, x1, z1`).
2. Attach the crop to ChatGPT and ask for a prompt that repaints it as a <style> map while keeping the
   framing, aspect, scale and every position and shape (river, bridges, streets, walls); no text,
   labels, compass or frame. Then generate.
3. Align the painting to the crop: `python scripts/align_to_layout.py painted.png layout_crop.png out.png`
   (OpenCV ECC affine on blurred gradient maps, mirrored borders; it prints the match score before and
   after). Check by overlaying the crop's edges on the result: rivers, bridges and walls should line up
   within a few pixels.
4. Ship `out.png` as the map texture with the world rectangle in the level JSON; the game converts the
   player's X/Z to image pixels with that rectangle and rotates the arrow to the hero's facing.
5. Verify in-game with screenshot tours at known landmarks (`--tour map,x,z,yaw`).
6. If the world changes later: re-render the plan, re-crop, repaint, re-align.

## Prompt style reminders

- Always start with the game's style block (01), end with `no text` (and `no labels`, `no frame` for maps).
- Scenes: `wide cinematic 16:9`. Characters: `full-body character sheet, front/side/back, neutral background`.
- Keep a consistent look by attaching the best earlier image: "keep exactly the same art style as the
  reference image".
- Don't ask for recreations of existing games' characters, logos or art; "in the style of" an era is fine.
