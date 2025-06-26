import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { StreamMessage } from "@/components/app/feedbox";

export function cn(...inputs: ClassValue[]) {
	return twMerge(clsx(inputs));
}

// Helper function to extract warning type from the message
export const getWarningType = (message: StreamMessage): string => {
	// You can customize this based on your actual warning types
	return message.warning_type || "Unknown Warning";
};

// Helper function to format timestamp
export const formatTimestamp = (timestamp: string): string => {
	return new Date(timestamp).toLocaleString();
};

// Helper function to extract repository info
export const getRepositoryInfo = (message: StreamMessage) => {
	const repoName = message.payload.repo?.name || "Unknown Repository";
	const repoUrl = message.payload.repo?.url || "#";

	return {
		name: repoName.split("/").pop() || repoName, // Get just the repo name without owner
		url: repoUrl.replace("api.github.com/repos", "github.com"), // Convert API URL to web URL
	};
};

// Helper function to extract actor info
export const getActorInfo = (message: StreamMessage) => {
	const actor = message.payload.actor;
	return {
		name: actor?.display_login || actor?.login || "Unknown User",
		username: actor?.login || "unknown",
		avatarUrl: actor?.avatar_url || "",
		profileUrl:
			actor?.url?.replace("api.github.com/users", "github.com") || "#",
	};
};
