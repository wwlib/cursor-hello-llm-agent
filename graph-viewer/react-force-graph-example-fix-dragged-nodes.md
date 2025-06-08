# react-force-graph-example-fix-dragged-nodes

```html
<head>
  <style> body { margin: 0; } </style>

  <script type="importmap">{ "imports": {
    "react": "https://esm.sh/react",
    "react-dom": "https://esm.sh/react-dom/client"
  }}</script>

<!--  <script type="module">import * as React from 'react'; window.React = React;</script>-->
<!--  <script src="../../src/packages/react-force-graph-3d/dist/react-force-graph-3d.js" defer></script>-->
</head>

<body>
  <div id="graph"></div>

  <script src="//cdn.jsdelivr.net/npm/@babel/standalone"></script>
  <script type="text/jsx" data-type="module">
    import ForceGraph3D from 'https://esm.sh/react-force-graph-3d?external=react';
    import React from 'react';
    import { createRoot } from 'react-dom';

    fetch('../datasets/miserables.json').then(res => res.json()).then(data => {
      createRoot(document.getElementById('graph')).render(
        <ForceGraph3D
          graphData={data}
          nodeLabel="id"
          nodeAutoColorBy="group"
          onNodeDragEnd={node => {
            node.fx = node.x;
            node.fy = node.y;
            node.fz = node.z;
          }}
        />
      );
    });
  </script>
</body>
```