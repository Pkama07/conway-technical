import { createClient } from "@supabase/supabase-js";

const browserSupabase = createClient(
	process.env.NEXT_PUBLIC_SUPABASE_URL!,
	process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

export const getRelevantEvents = async (query: string) => {
	const { data } = await browserSupabase
		.from("flagged_events")
		.select()
		.eq("has_been_processed", true)
		.or(
			`repo_name.ilike.%${query}%, org_name.ilike.%${query}%, actor_username.ilike.%${query}%`
		);
	return data;
};
