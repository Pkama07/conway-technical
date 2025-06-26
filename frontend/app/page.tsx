"use client";

import Title from "@/components/app/title";
import Feedbox, { StreamMessage } from "@/components/app/feedbox";
import Viewer from "@/components/app/viewer";
import { useEffect, useState } from "react";

export default function Home() {
	const [currEvent, setCurrEvent] = useState<StreamMessage | null>(null);

	return (
		<div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8 transition-colors duration-200">
			<Title />
			<div className="max-w-7xl mx-auto px-4 h-[calc(100vh-8rem)]">
				<div className="h-full flex flex-col lg:flex-row gap-6">
					{/* Left Section - Feedbox */}
					<div className="flex-1 lg:w-1/2 max-h-[60vh] lg:max-h-none">
						<Feedbox setCurrEvent={setCurrEvent} />
					</div>

					{/* Right Section - Viewer */}
					<div className="flex-1 lg:w-1/2 min-h-0">
						<Viewer currEvent={currEvent} />
					</div>
				</div>
			</div>
		</div>
	);
}
