"use client";

import { useEffect, useState } from "react";

export default function Home() {
	const [messages, setMessages] = useState<string[]>([]);

	useEffect(() => {
		const eventSource = new EventSource("http://127.0.0.1:8000/stream");

		eventSource.onmessage = (event) => {
			setMessages((prevMessages) => [event.data, ...prevMessages]);
		};

		eventSource.onerror = (error) => {
			console.error("EventSource failed:", error);
			eventSource.close();
		};

		return () => {
			eventSource.close();
		};
	}, []);

	return (
		<div>
			<p>list of messages</p>
			{messages.map((message, index) => (
				<div key={index}>{message}</div>
			))}
		</div>
	);
}
