# ~/public/ ontology
## Deployment Architecture (GitHub Pages)

```md
public/
├── .nojekyll
├── index.html      # FossilBones
├── script.js       # Muscles
└── style.css       # Plumage
```

## FossilBones TiddlyWiki + Feather + Fossil

To serve a Feather Wiki w/ FossilBones on GitHub Pages (without CSP issues):

1. Separate the layers (Bones/Plumage/Muscles into three files)
2. Add `.nojekyll` to bypass Jekyll processing
3. Use GitHub Actions with `actions/upload-pages-artifact@v3` pointing to the `public/` directory
4. Serve from `redirect` branch (or any branch configured in Pages settings)

## Manual-test
```md
# From project root
cd public

# Python 3's built-in server
python3 -m http.server 8000

# Or if you prefer Node.js (install if needed)
npx serve .
```
> Then open `http://localhost:8000` in your browser. This perfectly simulates GitHub Pages behavior (static file serving).

## TODO: Script-tset
```md
# 1. Start local server
cd public && python3 -m http.server 8000 &

# 2. Test with curl (checks if files are served)
curl -I http://localhost:8000/index.html | grep "200 OK"
curl -I http://localhost:8000/style.css | grep "200 OK"
curl -I http://localhost:8000/script.js | grep "200 OK"

# 3. Check HTML validity
npm install -g html-validate
html-validate index.html

# 4. Open in browser (if on Linux with GUI)
if command -v xdg-open &> /dev/null; then
  xdg-open http://localhost:8000
fi
```

# Python (preferred) version (future)

```md
# Step 1: Extract CSS from original.html (preserves comments)
# Using Python (most reliable, you have Python in the devcontainer)
python3 -c "
import re
with open('original.html', 'r') as f:
    content = f.read()
    css = re.search(r'<style>(.*?)</style>', content, re.DOTALL)
    if css:
        print(css.group(1).strip())
" > public/style.css

# Alternative using sed (if Python not available)
# sed -n '/<style>/,/<\/style>/p' original.html | sed '1s/.*<style>//; $s/<\/style>.*//' > public/style.css
```

# 2-stage 0.1.1 build system

```md
---
tag: 0.1.1
---

# Step 1: Extract CSS from original index.html
> sed -n '/<style>/,/<\/style>/p' original.html | sed '1s/.*<style>//; $s/<\/style>.*//' > public/style.css

# Step 2: Create minimal Bones HTML (index.html) with external references
> "Manual" (ideally script-based) editing to remove inline CSS/JS, add <link> and <script src>

# Step 3: Extract Muscles JS (everything after manifest)
> Copy from "/* Muscles — FW runtime */" to end of file > public/script.js

# Step 4: Keep manifest inline (it's data, not code)
> window.__FW_MANIFEST__ stays in index.html

# Step 5: Add .nojekyll to bypass GitHub Pages processing
> touch public/.nojekyll

# Step 6: Test locally
(see: `~/public/ontology.md`)
> cd public && python3 -m http.server 8000
```

# BEYOND 0.1.1
CICD and non-manual testing define the 0.x.y version-bump for FossilBones, for exampple:

```yml
- name: Create and push tag on successful deploy
  if: success()
  run: |
    git config user.name "github-actions[bot]"
    git config user.email "github-actions[bot]@users.noreply.github.com"
    TAG="v$(date +'%Y%m%d-%H%M%S')"
    git tag -a "$TAG" -m "Automated deploy from GitHub Actions run ${{ github.run_number }}"
    git push origin "$TAG"
```

Manual Alt:

```sh
# Tag a specific commit (e.g., after successful build)
git tag -a 0.1.1 -m "Successful build #${GITHUB_RUN_NUMBER}" c0eaaa5

# Push the tag
git push origin 0.1.1
```

# The Ironic part
## Versioning Strategy (Git → Fossil bridge)

Until we migrate to FossilBones fully, we use Git tags to track releases:

- **0.1.1** - Initial working release (CSP fix, bifurcated architecture)
- **0.1.1-fix1** - Patch: CSS extraction syntax, valid CSS comments
- **0.2.y** - Python scripting layer / SDK (future)

### Replacing a tag (fix a bug in a release)

```bash
# Delete old tag
git tag -d 0.1.1 && git push origin --delete 0.1.1

# Commit fixes
git add . && git commit -m "fix: patch for 0.1.1"

# Recreate tag at new HEAD
git tag -a 0.1.1 -m "Release 0.1.1 (patched: CSS fix)"

# Push new tag
git push origin 0.1.1
```
