'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Upload,
  FileText,
  Bot,
  Menu,
  X,
  Activity,
} from 'lucide-react';
import { FaAws } from 'react-icons/fa';

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Submit Request', href: '/upload', icon: Upload },
  { name: 'Cases', href: '/cases', icon: FileText },
  { name: 'AI Assistant', href: '/chat', icon: Bot },
];

export default function Navigation() {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <>
      {/* Desktop Sidebar */}
      <div className="hidden lg:fixed lg:inset-y-0 lg:z-50 lg:flex lg:w-72 lg:flex-col">
        <div className="flex grow flex-col gap-y-5 overflow-y-auto bg-gradient-to-b from-blue-600 to-blue-800 px-6 pb-4">
          <div className="flex h-16 shrink-0 items-center gap-3 mt-4">
            <Activity className="h-8 w-8 text-white" />
            <div>
              <h1 className="text-xl font-bold text-white">Syntrix AI</h1>
              <p className="text-xs text-blue-200">Prior Authorization System</p>
            </div>
          </div>
          <nav className="flex flex-1 flex-col">
            <ul role="list" className="flex flex-1 flex-col gap-y-7">
              <li>
                <ul role="list" className="-mx-2 space-y-1">
                  {navigation.map((item) => {
                    const isActive = pathname === item.href;
                    return (
                      <li key={item.name}>
                        <Link
                          href={item.href}
                          className={`
                            group flex gap-x-3 rounded-md p-3 text-sm font-semibold leading-6 transition-all
                            ${
                              isActive
                                ? 'bg-white text-blue-600 shadow-lg'
                                : 'text-blue-100 hover:text-white hover:bg-blue-700'
                            }
                          `}
                        >
                          <item.icon
                            className={`h-5 w-5 shrink-0 ${
                              isActive ? 'text-blue-600' : 'text-blue-300'
                            }`}
                          />
                          {item.name}
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              </li>
              <li className="mt-auto">
                <div className="bg-blue-700 rounded-lg p-4">
                  <p className="text-xs text-blue-200 mb-3">Built with</p>
                  <div className="flex items-center gap-3">
                    <div className="bg-black p-2 rounded-lg">
                      <FaAws className="h-6 w-6 text-white" />
                    </div>
                    <div>
                      <p className="text-base font-bold text-white leading-tight">AWS</p>
                      <p className="text-xs text-blue-200">Amazon Web Services</p>
                    </div>
                  </div>
                </div>
              </li>
            </ul>
          </nav>
        </div>
      </div>

      {/* Mobile menu button */}
      <div className="sticky top-0 z-40 flex items-center gap-x-6 bg-white px-4 py-4 shadow-sm sm:px-6 lg:hidden">
        <button
          type="button"
          className="-m-2.5 p-2.5 text-gray-700"
          onClick={() => setMobileMenuOpen(true)}
        >
          <span className="sr-only">Open sidebar</span>
          <Menu className="h-6 w-6" />
        </button>
        <div className="flex-1 flex items-center gap-2">
          <Activity className="h-6 w-6 text-blue-600" />
          <span className="text-sm font-semibold">Syntrix AI</span>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileMenuOpen && (
        <div className="relative z-50 lg:hidden">
          <div
            className="fixed inset-0 bg-gray-900/80"
            onClick={() => setMobileMenuOpen(false)}
          />
          <div className="fixed inset-0 flex">
            <div className="relative mr-16 flex w-full max-w-xs flex-1">
              <div className="absolute left-full top-0 flex w-16 justify-center pt-5">
                <button
                  type="button"
                  className="-m-2.5 p-2.5"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  <span className="sr-only">Close sidebar</span>
                  <X className="h-6 w-6 text-white" />
                </button>
              </div>
              <div className="flex grow flex-col gap-y-5 overflow-y-auto bg-gradient-to-b from-blue-600 to-blue-800 px-6 pb-4">
                <div className="flex h-16 shrink-0 items-center gap-3 mt-4">
                  <Activity className="h-8 w-8 text-white" />
                  <div>
                    <h1 className="text-xl font-bold text-white">Syntrix AI</h1>
                    <p className="text-xs text-blue-200">Prior Authorization</p>
                  </div>
                </div>
                <nav className="flex flex-1 flex-col">
                  <ul role="list" className="flex flex-1 flex-col gap-y-7">
                    <li>
                      <ul role="list" className="-mx-2 space-y-1">
                        {navigation.map((item) => {
                          const isActive = pathname === item.href;
                          return (
                            <li key={item.name}>
                              <Link
                                href={item.href}
                                onClick={() => setMobileMenuOpen(false)}
                                className={`
                                  group flex gap-x-3 rounded-md p-3 text-sm font-semibold leading-6
                                  ${
                                    isActive
                                      ? 'bg-white text-blue-600'
                                      : 'text-blue-100 hover:text-white hover:bg-blue-700'
                                  }
                                `}
                              >
                                <item.icon
                                  className={`h-5 w-5 shrink-0 ${
                                    isActive ? 'text-blue-600' : 'text-blue-300'
                                  }`}
                                />
                                {item.name}
                              </Link>
                            </li>
                          );
                        })}
                      </ul>
                    </li>
                  </ul>
                </nav>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

