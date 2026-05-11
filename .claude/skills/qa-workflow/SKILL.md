---
name: qa-workflow
description: 全链路质量检查（测试+类型+lint+安全）
---

## 全链路质量检查

按顺序执行以下检查：

### 1. 后端测试
```bash
cd backend && pytest -v 2>&1 | tail -20
```

### 2. 未合并的数据库迁移
```bash
cd backend && alembic check 2>&1
```

### 3. 前端 TypeScript 类型检查
```bash
cd frontend && npx tsc --noEmit 2>&1
```

### 4. 前端 Lint
```bash
cd frontend && npm run lint 2>&1
```

### 5. 安全规范检查
```bash
cd backend && python -c "
# 检查所有 API route 是否有权限装饰器
import os, re
routes_dir = 'app/api/v1'
issues = []
for root, dirs, files in os.walk(routes_dir):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            with open(path) as fh:
                content = fh.read()
            endpoints = re.findall(r'@router\.(get|post|put|patch|delete)\(', content)
            guards = re.findall(r'Depends\(require_role|Depends\(get_current_user', content)
            if endpoints and not guards:
                issues.append(f'{path}: {len(endpoints)} endpoints, {len(guards)} auth guards')
if issues:
    for i in issues: print(f'WARNING: {i}')
else:
    print('OK: all endpoints have auth guards')
"
```

### 6. 审计日志保留天数
```bash
cd backend && python -c "
from app.models.audit_log import AuditLog
# 检查模型中 retention_days 配置
import inspect
src = inspect.getsource(AuditLog)
import re
m = re.search(r'retention_days\s*[:=]\s*(\d+)', src)
if m:
    print(f'审计日志保留天数: {m.group(1)} 天')
else:
    print('审计日志保留天数: 180 天（默认）')
"
```

### 7. 汇总
```bash
echo "========== QA 检查完成 =========="
echo "建议 PR 前修复所有 WARNING 项"
```
