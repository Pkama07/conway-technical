"use client";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { ExternalLink, GitBranch, AlertTriangle, Clock } from "lucide-react";

interface WarningCardProps {
	id: string;
	warningType: string;
	repository: {
		name: string;
		url: string;
	};
	actor: {
		name: string;
		username: string;
		avatarUrl: string;
		profileUrl: string;
	};
	timestamp: string;
	isProcessed: boolean;
	analysis?: {
		rootCause: string[];
		impact: string[];
		nextSteps: string[];
	};
	isViewed?: boolean;
}

export default function WarningCard({
	warningType,
	repository,
	actor,
	timestamp,
	isProcessed,
	analysis,
	isViewed = false,
}: WarningCardProps) {
	const getWarningTypeColor = (type: string) => {
		switch (type.toLowerCase()) {
			case "Push to default branch":
				return "bg-red-100 text-red-800 border-red-200";
			case "Large push to default branch":
				return "bg-orange-100 text-orange-800 border-orange-200";
			case "Default branch deleted":
				return "bg-yellow-100 text-yellow-800 border-yellow-200";
			case "Repository visibility changed to public":
				return "bg-blue-100 text-blue-800 border-blue-200";
			case "New collaborator added":
				return "bg-green-100 text-green-800 border-green-200";
			default:
				return "bg-gray-100 text-gray-800 border-gray-200";
		}
	};

	return (
		<Card
			className={`w-full max-w-2xl mx-auto mb-4 transition duration-200 shadow-sm bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 ${
				!isViewed
					? "hover:shadow-md hover:bg-gray-100 dark:hover:bg-gray-700"
					: ""
			}`}
		>
			<CardHeader>
				<div className="flex items-start justify-between gap-3">
					<div className="flex-1 min-w-0">
						<div className="flex items-center gap-2 mb-2">
							<Badge
								variant="outline"
								className={`${getWarningTypeColor(warningType)} font-medium`}
							>
								<AlertTriangle className="w-3 h-3 mr-1" />
								{warningType}
							</Badge>
						</div>

						<div className="flex items-center gap-2 text-sm text-muted-foreground dark:text-gray-400 mb-1">
							<GitBranch className="w-4 h-4" />
							<a
								href={repository.url}
								target="_blank"
								rel="noopener noreferrer"
								className="font-medium text-foreground dark:text-gray-200 hover:underline flex items-center gap-1"
							>
								{repository.name}
								<ExternalLink className="w-3 h-3" />
							</a>
						</div>

						<div className="flex items-center gap-2 text-sm text-muted-foreground dark:text-gray-400">
							<Clock className="w-4 h-4" />
							{timestamp}
						</div>
					</div>

					<div className="flex items-center gap-2 flex-shrink-0">
						<Avatar className="w-8 h-8">
							<AvatarImage
								src={actor.avatarUrl || "/placeholder.svg"}
								alt={actor.name}
							/>
							<AvatarFallback>
								{actor.name.charAt(0).toUpperCase()}
							</AvatarFallback>
						</Avatar>
						<div className="text-right">
							<a
								href={actor.profileUrl}
								target="_blank"
								rel="noopener noreferrer"
								className="text-sm font-medium hover:underline flex items-center gap-1"
							>
								{actor.name}
								<ExternalLink className="w-3 h-3" />
							</a>
							<div className="text-xs text-muted-foreground dark:text-gray-400">
								@{actor.username}
							</div>
						</div>
					</div>
				</div>
			</CardHeader>

			<Separator />

			<CardContent>
				{!isProcessed ? (
					<div className="flex items-center justify-center py-8">
						<div className="text-center">
							<div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary dark:border-blue-400 mx-auto mb-3"></div>
							<p className="text-muted-foreground dark:text-gray-400">
								This warning is being processed...
							</p>
							<p className="text-sm text-muted-foreground dark:text-gray-400 mt-1">
								Analysis will be available shortly
							</p>
						</div>
					</div>
				) : (
					analysis && (
						<div className="space-y-6">
							<div>
								<h4 className="font-semibold text-sm text-red-700 mb-2 flex items-center gap-2">
									<div className="w-2 h-2 bg-red-500 rounded-full"></div>
									Root Cause
								</h4>
								<ul className="space-y-1 ml-4">
									{analysis.rootCause.map((item, index) => (
										<li
											key={index}
											className="text-sm text-muted-foreground dark:text-gray-400 flex items-start gap-2"
										>
											<ul className="list-disc list-inside">
												<li>{item}</li>
											</ul>
										</li>
									))}
								</ul>
							</div>

							<div>
								<h4 className="font-semibold text-sm text-orange-700 mb-2 flex items-center gap-2">
									<div className="w-2 h-2 bg-orange-500 rounded-full"></div>
									Impact
								</h4>
								<ul className="space-y-1 ml-4">
									{analysis.impact.map((item, index) => (
										<li
											key={index}
											className="text-sm text-muted-foreground dark:text-gray-400 flex items-start gap-2"
										>
											<ul className="list-disc list-inside">
												<li>{item}</li>
											</ul>
										</li>
									))}
								</ul>
							</div>

							<div>
								<h4 className="font-semibold text-sm text-blue-700 mb-2 flex items-center gap-2">
									<div className="w-2 h-2 bg-blue-500 rounded-full"></div>
									Next Steps
								</h4>
								<ul className="space-y-1 ml-4">
									{analysis.nextSteps.map((item, index) => (
										<li
											key={index}
											className="text-sm text-muted-foreground dark:text-gray-400 flex items-start gap-2"
										>
											<ul className="list-disc list-inside">
												<li>{item}</li>
											</ul>
										</li>
									))}
								</ul>
							</div>
						</div>
					)
				)}
			</CardContent>
		</Card>
	);
}
