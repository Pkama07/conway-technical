"use client";

import { createContext, useContext, useEffect, useState } from "react";

interface DarkModeContextType {
	isDarkMode: boolean;
	toggleDarkMode: () => void;
}

const DarkModeContext = createContext<DarkModeContextType | undefined>(
	undefined
);

export function DarkModeProvider({ children }: { children: React.ReactNode }) {
	const [isDarkMode, setIsDarkMode] = useState(false);

	// Load dark mode preference from localStorage on mount
	useEffect(() => {
		const saved = localStorage.getItem("darkMode");
		if (saved) {
			setIsDarkMode(JSON.parse(saved));
		} else {
			// Check system preference
			setIsDarkMode(window.matchMedia("(prefers-color-scheme: dark)").matches);
		}
	}, []);

	// Apply dark mode class to document
	useEffect(() => {
		if (isDarkMode) {
			document.documentElement.classList.add("dark");
		} else {
			document.documentElement.classList.remove("dark");
		}
		localStorage.setItem("darkMode", JSON.stringify(isDarkMode));
	}, [isDarkMode]);

	const toggleDarkMode = () => {
		setIsDarkMode(!isDarkMode);
	};

	return (
		<DarkModeContext.Provider value={{ isDarkMode, toggleDarkMode }}>
			{children}
		</DarkModeContext.Provider>
	);
}

export function useDarkMode() {
	const context = useContext(DarkModeContext);
	if (context === undefined) {
		throw new Error("useDarkMode must be used within a DarkModeProvider");
	}
	return context;
}
