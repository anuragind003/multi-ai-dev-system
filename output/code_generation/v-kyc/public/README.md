# Public Assets Directory

This directory contains static assets that are served directly by the web server.

## Logo Image

To add the L&T Finance logo:

1. **Copy your logo image** to this directory
2. **Rename it to** `L&T.jpg`
3. **Ensure it's accessible** at `/L&T.jpg` in your application

### Supported Formats
- JPG/JPEG (recommended)
- PNG
- SVG
- WebP

### Recommended Dimensions
- **Login page**: 200x80 pixels
- **Dashboard header**: 120x48 pixels
- **High resolution**: 400x160 pixels (for retina displays)

### File Structure
```
public/
├── L&T.jpg          # Your logo image here
└── README.md        # This file
```

The logo will automatically appear on:
- Login page (centered, larger size)
- Dashboard header (left side, smaller size) 