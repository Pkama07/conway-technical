"use client";

import { useEffect, useState } from "react";
import WarningCard from "@/components/app/warning-card";
import { getRelevantEvents } from "@/lib/supabase/client";
import {
	getWarningType,
	getRepositoryInfo,
	getActorInfo,
	formatTimestamp,
} from "@/lib/utils";

export interface StreamMessage {
	payload: {
		id: string;
		type: string;
		actor: {
			id: number;
			login: string;
			display_login?: string;
			avatar_url: string;
			url: string;
		};
		repo: {
			id: number;
			name: string;
			url: string;
		};
		created_at: string;
		[key: string]: unknown;
	};
	analysis?: {
		root_cause: string[];
		impact: string[];
		next_steps: string[];
	};
	warning_id: string;
	warning_type: string;
	is_ping: boolean;
}

interface FeedboxProps {
	setCurrEvent: (event: StreamMessage | null) => void;
}

export default function Feedbox({ setCurrEvent }: FeedboxProps) {
	const [messages, setMessages] = useState<StreamMessage[]>([]);
	const [activeTab, setActiveTab] = useState<"feed" | "search">("feed");
	const [searchQuery, setSearchQuery] = useState("");
	const [searchResults, setSearchResults] = useState<StreamMessage[]>([]);
	const [isLoading, setIsLoading] = useState(false);

	useEffect(() => {
		const eventSource = new EventSource(process.env.NEXT_PUBLIC_BACKEND_URL!);

		eventSource.onmessage = (event) => {
			try {
				const data = JSON.parse(event.data);
				if (data.payload && data.is_ping == false) {
					setMessages((prevMessages) => {
						const newMessages = [data, ...prevMessages].slice(0, 20);
						return newMessages;
					});
				}
			} catch (error) {
				console.log(error);
			}
		};

		eventSource.onerror = (error) => {
			console.error(error);
			console.error("EventSource failed:", error);
			eventSource.close();
		};

		return () => {
			eventSource.close();
		};
	}, []);

	// Search function - implement your search logic here
	const handleSearch = async (query: string) => {
		setIsLoading(true);
		const data = await getRelevantEvents(query);
		const newSearchResults: StreamMessage[] = [];
		if (data) {
			newSearchResults.push(
				...data.map((event) => ({
					warning_id: event.id,
					warning_type: event.type,
					payload: event.event_payload,
					analysis: {
						root_cause: event.root_cause,
						impact: event.impact,
						next_steps: event.next_steps,
					},
					is_ping: false,
				}))
			);
		}
		setSearchResults(newSearchResults);
		setIsLoading(false);
	};

	// Auto-search effect
	useEffect(() => {
		if (activeTab === "search" && searchQuery.trim()) {
			const debounceTimer = setTimeout(() => {
				handleSearch(searchQuery);
			}, 300); // 300ms debounce

			return () => clearTimeout(debounceTimer);
		} else if (activeTab === "search" && !searchQuery.trim()) {
			setSearchResults([]);
		}
	}, [searchQuery, activeTab]);

	return (
		<div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden h-full flex flex-col transition-colors duration-200">
			<div className="p-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700 h-20 flex items-center flex-shrink-0">
				<div className="flex items-center justify-between w-full">
					<h2 className="text-lg font-semibold text-gray-800 dark:text-gray-200">
						{activeTab === "feed"
							? `Recent Warnings (${messages.length})`
							: "Search Results"}
					</h2>
					<div className="relative flex bg-gray-200 dark:bg-gray-600 rounded-full p-1">
						{/* Animated background bubble */}
						<div
							className={`absolute top-1 bottom-1 bg-white dark:bg-gray-800 rounded-full shadow-sm transition-all duration-300 ease-out ${
								activeTab === "feed" ? "left-1 right-1/2" : "left-1/2 right-1"
							}`}
						/>
						<button
							onClick={() => setActiveTab("feed")}
							className={`relative z-10 pl-5 py-2 rounded-full text-sm font-medium transition-all duration-200 ${
								activeTab === "feed"
									? "text-gray-900 dark:text-gray-100"
									: "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
							}`}
						>
							Feed
						</button>
						<button
							onClick={() => setActiveTab("search")}
							className={`relative z-10 pl-10 px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 ${
								activeTab === "search"
									? "text-gray-900 dark:text-gray-100"
									: "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
							}`}
						>
							Search
						</button>
					</div>
				</div>
			</div>

			{activeTab === "search" && (
				<div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden animate-in slide-in-from-top-2 duration-500 ease-out flex-shrink-0">
					<div className="relative">
						<div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
							<svg
								className="h-5 w-5 text-gray-400 dark:text-gray-500"
								fill="none"
								viewBox="0 0 24 24"
								stroke="currentColor"
							>
								<path
									strokeLinecap="round"
									strokeLinejoin="round"
									strokeWidth={2}
									d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
								/>
							</svg>
						</div>
						<input
							type="text"
							placeholder="Search warnings..."
							value={searchQuery}
							onChange={(e) => setSearchQuery(e.target.value)}
							className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent outline-none"
						/>
					</div>
				</div>
			)}

			<div className="flex-1 min-h-0 overflow-y-auto">
				{activeTab === "feed" ? (
					// Feed Tab Content
					messages.length === 0 ? (
						<div className="p-12 text-center text-gray-500 dark:text-gray-400">
							<div className="animate-pulse">
								<div className="text-lg mb-2">
									Connecting to the event stream...
								</div>
								<div className="text-sm">
									The feed will update automatically when new warnings are
									detected.
								</div>
							</div>
						</div>
					) : (
						<div className="space-y-4 p-4">
							{messages.map((message, index) => (
								<div
									key={`${message.warning_id}-${index}`}
									onClick={() => setCurrEvent(message)}
									className={`cursor-pointer transition-all duration-500 ease-out ${
										index === 0 ? "animate-in slide-in-from-top-4" : ""
									}`}
								>
									<WarningCard
										id={message.warning_id}
										warningType={getWarningType(message)}
										repository={getRepositoryInfo(message)}
										actor={getActorInfo(message)}
										timestamp={formatTimestamp(message.payload.created_at)}
										isProcessed={!!message.analysis}
										analysis={
											message.analysis
												? {
														rootCause: message.analysis.root_cause,
														impact: message.analysis.impact,
														nextSteps: message.analysis.next_steps,
												  }
												: undefined
										}
									/>
								</div>
							))}
						</div>
					)
				) : // Search Tab Content
				searchResults.length === 0 ? (
					isLoading ? (
						<div className="p-12 text-center text-gray-500 dark:text-gray-400">
							<div className="animate-pulse">
								<div className="text-lg mb-2">Loading search results...</div>
							</div>
						</div>
					) : (
						<div className="p-12 text-center text-gray-500 dark:text-gray-400">
							<div className="text-lg mb-2">No search results</div>
							<div className="text-sm">
								{searchQuery
									? "Try adjusting your search terms or filters."
									: "Enter a search query above to find warnings."}
							</div>
						</div>
					)
				) : (
					<div className="space-y-4 p-4">
						{searchResults.map((message, index) => (
							<div
								key={`search-${message.warning_id}-${index}`}
								onClick={() => setCurrEvent(message)}
								className="cursor-pointer transition-all duration-200 ease-out"
							>
								<WarningCard
									id={message.warning_id}
									warningType={getWarningType(message)}
									repository={getRepositoryInfo(message)}
									actor={getActorInfo(message)}
									timestamp={formatTimestamp(message.payload.created_at)}
									isProcessed={!!message.analysis}
									analysis={
										message.analysis
											? {
													rootCause: message.analysis.root_cause,
													impact: message.analysis.impact,
													nextSteps: message.analysis.next_steps,
											  }
											: undefined
									}
								/>
							</div>
						))}
					</div>
				)}
			</div>

			{activeTab === "feed" && messages.length >= 20 && (
				<div className="p-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700 text-center text-sm text-gray-600 dark:text-gray-300">
					Showing latest 20 warnings. Older warnings are automatically removed.
				</div>
			)}

			{activeTab === "search" && searchResults.length > 0 && (
				<div className="p-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700 text-center text-sm text-gray-600 dark:text-gray-300">
					Found {searchResults.length} result
					{searchResults.length !== 1 ? "s" : ""}
				</div>
			)}
		</div>
	);
}
