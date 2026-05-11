import { useEffect, useState, useCallback } from "react";
import { Card, Table, Checkbox, Button, Space, message, Spin, Divider } from "antd";
import { SaveOutlined, SafetyCertificateOutlined } from "@ant-design/icons";
import { getPermissionMatrix, updateRoleMenus } from "../../api/permissions";
import type { RolePermission, MenuItem } from "../../types";

export function PermissionsPage() {
  const [roles, setRoles] = useState<RolePermission[]>([]);
  const [menus, setMenus] = useState<MenuItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);

  // Local editable copy
  const [editMap, setEditMap] = useState<Record<number, Set<string>>>({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getPermissionMatrix();
      const body = res.data?.data;
      if (body) {
        setRoles(body.roles ?? []);
        setMenus(body.menus ?? []);
        const map: Record<number, Set<string>> = {};
        for (const r of body.roles) {
          map[r.role_id] = new Set(r.menu_keys);
        }
        setEditMap(map);
      }
    } catch {
      message.error("加载权限数据失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const toggle = (roleId: number, menuKey: string) => {
    setEditMap((prev) => {
      const next = new Set(prev[roleId]);
      if (next.has(menuKey)) {
        next.delete(menuKey);
      } else {
        next.add(menuKey);
      }
      return { ...prev, [roleId]: next };
    });
    setDirty(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      for (const r of roles) {
        const keys = Array.from(editMap[r.role_id] ?? []);
        await updateRoleMenus(r.role_id, keys);
      }
      message.success("权限配置已保存");
      setDirty(false);
      load();
    } catch {
      message.error("保存失败");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: 400 }}>
        <Spin size="large" />
      </div>
    );
  }

  const columns = [
    {
      title: "菜单",
      dataIndex: "label",
      key: "label",
      width: 160,
      render: (_: string, record: MenuItem) => <strong>{record.label}</strong>,
    },
    ...roles.map((role) => ({
      title: (
        <span>
          {role.role_name === "admin"
            ? "管理员"
            : role.role_name === "lawyer"
              ? "律师"
              : "普通用户"}
        </span>
      ),
      key: role.role_name,
      width: 120,
      render: (_: unknown, menu: MenuItem) => {
        const checked = editMap[role.role_id]?.has(menu.key) ?? false;
        return (
          <Checkbox
            checked={checked}
            onChange={() => toggle(role.role_id, menu.key)}
          />
        );
      },
    })),
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card
        title={
          <span>
            <SafetyCertificateOutlined /> 权限管理
          </span>
        }
        extra={
          <Button
            type="primary"
            icon={<SaveOutlined />}
            onClick={handleSave}
            loading={saving}
            disabled={!dirty}
          >
            保存权限配置
          </Button>
        }
      >
        <Table
          dataSource={menus}
          columns={columns}
          rowKey="key"
          pagination={false}
          bordered
          size="middle"
        />
      </Card>
    </div>
  );
}
