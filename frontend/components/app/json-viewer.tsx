import { Card, CardContent } from "@/components/ui/card";

import { StreamMessage } from "@/components/app/feedbox";

interface JsonViewerProps {
	currEvent: StreamMessage | null;
}

export default function JsonViewer({ currEvent }: JsonViewerProps) {
	const formatJsonWithLineNumbers = (
		obj: unknown
	): { number: number; content: string }[] => {
		if (!obj) return [];

		const jsonString = JSON.stringify(obj, null, 2);
		const lines = jsonString.split("\n");

		return lines.map((line, index) => ({
			number: index + 1,
			content: line,
		}));
	};

	const jsonLines = currEvent
		? formatJsonWithLineNumbers(currEvent.payload)
		: [];

	return (
		<div className="flex-1 min-h-[40vh] lg:min-h-0">
			<Card className="h-full shadow-sm overflow-scroll pb-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
				<CardContent className="h-full pb-4">
					<div className="h-full overflow-scroll">
						{currEvent ? (
							<div className="h-full bg-gray-50 dark:bg-gray-700 rounded-lg border border-gray-200 dark:border-gray-600 overflow-auto">
								<pre className="text-sm font-mono p-4 pb-6">
									{jsonLines.map(({ number, content }) => (
										<div
											key={number}
											className="flex hover:bg-gray-100 dark:hover:bg-gray-600"
										>
											<div className="w-12 text-right pr-4 text-gray-400 dark:text-gray-500 select-none flex-shrink-0 border-r border-gray-200 dark:border-gray-600">
												{number}
											</div>
											<div className="pl-4 flex-1 min-w-0">
												<code className="text-gray-800 dark:text-gray-200 break-all">
													{content}
												</code>
											</div>
										</div>
									))}
								</pre>
							</div>
						) : (
							<div className="h-full bg-gray-50 dark:bg-gray-700 rounded-lg border border-gray-200 dark:border-gray-600 flex items-center justify-center">
								<div className="text-center">
									<div className="text-lg font-medium text-gray-500 dark:text-gray-400 mb-2">
										No Event Selected
									</div>
									<div className="text-sm text-gray-400 dark:text-gray-500">
										JSON payload will appear here when an event is selected
									</div>
								</div>
							</div>
						)}
					</div>
				</CardContent>
			</Card>
		</div>
	);
}
