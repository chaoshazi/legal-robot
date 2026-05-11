import { useEffect } from "react";
import { Spin } from "antd";
import { useRoutes } from "react-router-dom";
import { routerConfig } from "./router";
import { useAuthStore } from "./stores/authStore";

export default function App() {
  const restoreUser = useAuthStore((s) => s.restoreUser);
  const isRestoring = useAuthStore((s) => s.isRestoring);

  useEffect(() => {
    restoreUser();
  }, [restoreUser]);

  if (isRestoring) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "100vh",
        }}
      >
        <Spin size="large" />
      </div>
    );
  }

  return useRoutes(routerConfig);
}
