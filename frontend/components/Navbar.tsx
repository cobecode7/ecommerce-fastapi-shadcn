"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";

export default function Navbar() {
  const { token, username, logout } = useAuth();

  return (
    <nav className="bg-white dark:bg-gray-900 border-b">
      <div className="container mx-auto px-4">
        <div className="flex justify-between items-center h-16">
          <Link href="/" passHref>
            <span className="text-2xl font-bold cursor-pointer">E-Commerce</span>
          </Link>
          <div className="flex items-center space-x-4">
            {token ? (
              <>
                <span className="text-sm">Welcome, {username}</span>
                <Button variant="ghost" onClick={logout}>Logout</Button>
              </>
            ) : (
              <>
                <Link href="/login" passHref>
                  <Button variant="ghost">Login</Button>
                </Link>
                <Link href="/register" passHref>
                  <Button variant="ghost">Register</Button>
                </Link>
              </>
            )}
            <Link href="/cart" passHref>
               <Button variant="outline">Cart</Button>
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}
