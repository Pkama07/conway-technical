"use client";

import { StreamMessage } from "./feedbox";
import WarningCard from "./warning-card";
import { Card, CardHeader } from "@/components/ui/card";
import {
	getWarningType,
	getRepositoryInfo,
	getActorInfo,
	formatTimestamp,
} from "@/lib/utils";
import JsonViewer from "@/components/app/json-viewer";

interface ViewerProps {
	currEvent: StreamMessage | null;
}

export default function Viewer({ currEvent }: ViewerProps) {
	return (
		<div className="flex flex-col h-full gap-4">
			{/* Warning Card Section */}
			<div className="lg:h-[50%] lg:overflow-hidden">
				<div className="lg:h-full lg:overflow-y-auto lg:w-auto w-full">
					{currEvent ? (
						<WarningCard
							id={currEvent.warning_id}
							warningType={getWarningType(currEvent)}
							repository={getRepositoryInfo(currEvent)}
							actor={getActorInfo(currEvent)}
							timestamp={formatTimestamp(currEvent.payload.created_at)}
							isProcessed={!!currEvent.analysis}
							analysis={
								currEvent.analysis
									? {
											rootCause: currEvent.analysis.root_cause,
											impact: currEvent.analysis.impact,
											nextSteps: currEvent.analysis.next_steps,
									  }
									: undefined
							}
							isViewed={true}
						/>
					) : (
						<Card className="w-full shadow-sm lg:h-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
							<CardHeader className="h-full flex flex-col items-center">
								<div className="text-center flex flex-col justify-center py-8 h-full">
									<div className="text-lg font-medium text-gray-500 dark:text-gray-400">
										No Event Selected
									</div>
									<div className="text-sm text-gray-400 dark:text-gray-500">
										Click on a warning from the feed to view details
									</div>
								</div>
							</CardHeader>
						</Card>
					)}
				</div>
			</div>

			{/* JSON Viewer Section */}
			<JsonViewer currEvent={currEvent} />
		</div>
	);
}
