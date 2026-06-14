# ~/public/ ontology

```md
public/
├── .nojekyll
├── index.html      # FossilBones
├── script.js       # Muscles
└── style.css       # Plumage
```


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
