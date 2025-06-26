"use client";

import { useDarkMode } from "@/lib/dark-mode-context";
import { Moon, Sun } from "lucide-react";

export default function Title() {
	const { isDarkMode, toggleDarkMode } = useDarkMode();

	return (
		<div className="mb-8 flex items-center justify-between gap-4 px-8">
			{/* Dark Mode Toggle Button */}

			<div></div>

			{/* Title Content */}
			<div className="text-center">
				<h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
					GitHub Event Monitor
				</h1>
				<p className="text-gray-600 dark:text-gray-400">
					Real-time monitoring of flagged GitHub events
				</p>
			</div>

			<button
				onClick={toggleDarkMode}
				className="p-2 rounded-lg bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 transition-colors duration-200"
				aria-label="Toggle dark mode"
			>
				{isDarkMode ? (
					<Sun className="h-5 w-5 text-gray-700 dark:text-gray-200" />
				) : (
					<Moon className="h-5 w-5 text-gray-700 dark:text-gray-200" />
				)}
			</button>
		</div>
	);
}
