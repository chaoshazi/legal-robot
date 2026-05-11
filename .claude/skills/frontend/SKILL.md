---
name: frontend
description: 前端开发与调试
---

## 前端开发辅助

### 1. TypeScript 类型检查
```bash
cd frontend && npx tsc --noEmit
```

### 2. Lint 检查
```bash
cd frontend && npm run lint
```

### 3. 开发构建
```bash
cd frontend && npm run build 2>&1 | tail -10
```

### 4. 查看前端路由结构
```bash
cd frontend && grep -r "path:" src/router/ | head -20
```

### 5. 查看全部 API 调用
```bash
cd frontend && grep -rn "client\.\(get\|post\|put\|patch\|delete\)" src/api/ | head -30
```

### 6. 查看 Zustand Store 结构
```bash
cd frontend && cat src/stores/authStore.ts
```

### 7. 查看页面组件清单
```bash
cd frontend && ls src/pages/*/ | head -20
```
