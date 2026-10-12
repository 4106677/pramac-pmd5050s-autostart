import sys, zlib, struct, numpy as np, trimesh
def save_png(path, img):
    h, w, _ = img.shape
    raw = b"".join(b"\x00" + img[y].tobytes() for y in range(h))
    def chunk(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    open(path, "wb").write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))
def render(meshes, rot, out, colors, size=(1500, 1100), scale=None):
    allv = np.vstack([m.vertices for m in meshes]); c = (allv.min(0) + allv.max(0)) / 2
    ax, az = np.radians(rot[0]), np.radians(rot[2])
    Rx = np.array([[1,0,0],[0,np.cos(ax),-np.sin(ax)],[0,np.sin(ax),np.cos(ax)]])
    Rz = np.array([[np.cos(az),-np.sin(az),0],[np.sin(az),np.cos(az),0],[0,0,1]])
    R = Rx @ Rz
    span = np.ptp((allv - c) @ R.T, axis=0)
    s = scale or min(size[0] / span[0], size[1] / span[1]) * 0.92
    W, H = size
    img = np.full((H, W, 3), 255.0); zb = np.full((H, W), -1e9)
    light = np.array([0.3, -0.5, 0.8]); light /= np.linalg.norm(light)
    for m, col in zip(meshes, colors):
        v = (m.vertices - c) @ R.T
        N = m.face_normals @ R.T
        for f, n in zip(m.faces, N):
            p = v[f]
            xs = W / 2 + p[:, 0] * s; ys = H / 2 - p[:, 1] * s
            x0, x1 = int(max(0, np.floor(xs.min()))), int(min(W - 1, np.ceil(xs.max())))
            y0, y1 = int(max(0, np.floor(ys.min()))), int(min(H - 1, np.ceil(ys.max())))
            if x1 < x0 or y1 < y0: continue
            gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            d = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
            if abs(d) < 1e-9: continue
            l1 = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / d
            l2 = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / d
            l3 = 1 - l1 - l2
            inside = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
            if not inside.any(): continue
            z = l1 * p[0, 2] + l2 * p[1, 2] + l3 * p[2, 2]
            sub = zb[y0:y1 + 1, x0:x1 + 1]
            upd = inside & (z > sub)
            k = 0.3 + 0.7 * max(0.0, float(n @ light))
            sub[upd] = z[upd]
            img[y0:y1 + 1, x0:x1 + 1][upd] = np.array(col) * k
    valid = zb > -1e8
    if valid.any():
        z0, z1 = zb[valid].min(), zb[valid].max()
        fog = 0.45 + 0.55 * (zb - z0) / max(z1 - z0, 1e-6)
        img[valid] = img[valid] * fog[valid][:, None]
    save_png(out, np.clip(img, 0, 255).astype(np.uint8))
if __name__ == "__main__":
    b = trimesh.load("base.stl"); l = trimesh.load("lid.stl"); cv = trimesh.load("cover.stl")
    gray, lg, red = (205, 205, 210), (235, 235, 240), (210, 45, 45)
    l2 = l.copy(); l2.apply_translation([0, 0, 50.2 + 28])
    cv2 = cv.copy(); cv2.apply_translation([0, 0, 50.2 + 28 + 2.6 + 14])
    render([b], (-55, 0, 25), "iso_base.png", [gray])
    render([b, l2, cv2], (-62, 0, 22), "iso_all.png", [gray, lg, red], size=(1500, 1500))
    render([b], (0, 0, 0), "top_base.png", [gray])
    cv3 = cv.copy(); cv3.apply_translation([0, 0, 2.6])
    render([l, cv3], (0, 0, 0), "top_lid.png", [lg, red])
