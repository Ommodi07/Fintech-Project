"use client";

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarFooter,
  SidebarRail,
} from "@repo/ui/components/sidebar";
import { Activity, FileUp, LogOut, Target, User, Wallet } from "lucide-react";
import { authClient } from "@/lib/authApi";
import { useSignOut } from "@/lib/hooks/useAuth";
import { Button } from "@repo/ui/components/button";

const navItems = [
  { id: "overview" as const, title: "Overview", icon: Activity },
  { id: "upload" as const, title: "Upload", icon: FileUp },
  { id: "goal" as const, title: "Goal", icon: Target },
] as const;

export function AppSidebar({
  activeView,
  onViewChange,
}: {
  activeView: "overview" | "upload" | "goal";
  onViewChange: (view: "overview" | "upload" | "goal") => void;
}) {
  const { data: session } = authClient.useSession();
  const signOut = useSignOut();

  const user = session?.user;

  return (
    <Sidebar collapsible="icon">
      <SidebarRail />
      <SidebarHeader className="border-b border-sidebar-border">
        <div className="flex items-center gap-2 px-2 py-2">
          <div className="flex size-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground">
            <Wallet className="size-4" />
          </div>
          <div className="flex flex-col gap-0.5 leading-none group-data-[collapsible=icon]:hidden">
            <span className="font-semibold">Fintech</span>
            <span className="text-xs text-muted-foreground">Dashboard</span>
          </div>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => {
                const Icon = item.icon;
                return (
                  <SidebarMenuItem key={item.id}>
                    <SidebarMenuButton
                      isActive={activeView === item.id}
                      onClick={() => onViewChange(item.id)}
                      tooltip={item.title}
                    >
                      <Icon className="size-4" />
                      <span>{item.title}</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter className="border-t border-sidebar-border">
        {user && (
          <div className="group-data-[collapsible=icon]:hidden flex flex-col gap-2 p-2">
            <div className="flex items-center gap-2 rounded-lg px-2 py-2">
              {user.image ? (
                <img
                  src={user.image}
                  alt=""
                  className="size-8 rounded-full object-cover"
                />
              ) : (
                <div className="flex size-8 items-center justify-center rounded-full bg-sidebar-accent text-sidebar-accent-foreground">
                  <User className="size-4" />
                </div>
              )}
              <div className="flex min-w-0 flex-1 flex-col gap-0.5 overflow-hidden">
                <span className="truncate text-sm font-medium">
                  {user.name ?? "User"}
                </span>
                <span className="truncate text-xs text-muted-foreground">
                  {user.email}
                </span>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="w-full justify-start gap-2 text-muted-foreground hover:text-foreground"
              onClick={() => signOut.mutate()}
              disabled={signOut.isPending}
            >
              <LogOut className="size-4" />
              <span>{signOut.isPending ? "Signing out..." : "Log out"}</span>
            </Button>
          </div>
        )}
        {user && (
          <div className="group-data-[collapsible=icon]:flex hidden justify-center p-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => signOut.mutate()}
              disabled={signOut.isPending}
              title="Log out"
            >
              <LogOut className="size-4" />
            </Button>
          </div>
        )}
      </SidebarFooter>
    </Sidebar>
  );
}
