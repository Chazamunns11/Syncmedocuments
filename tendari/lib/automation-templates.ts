// Automation templates — plain data, shared by the server actions and the page.
// (Kept out of the "use server" file, which may only export async functions.)

export type Step = Record<string, unknown>;
export type Template = { name: string; trigger_type: string; steps: Step[] };

export const TEMPLATES: Record<string, Template> = {
  lead_followup: {
    name: "Lead follow-up reminder",
    trigger_type: "contact_created",
    steps: [
      { type: "wait", days: 1 },
      { type: "create_task", title: "Follow up with {name}", offset_days: 0 },
      { type: "notify", title: "Follow-up due", body: "Time to follow up with {name}" },
    ],
  },
  tag_leads: {
    name: "Tag new contacts as “Lead”",
    trigger_type: "contact_created",
    steps: [{ type: "add_tag", name: "Lead" }],
  },
  booking_prep: {
    name: "Prep task for new bookings",
    trigger_type: "booking_created",
    steps: [
      { type: "create_task", title: "Prepare for call with {name}" },
      { type: "notify", title: "New booking", body: "Get ready for {name}" },
    ],
  },
  welcome: {
    name: "Welcome new contacts",
    trigger_type: "contact_created",
    steps: [{ type: "notify", title: "New contact", body: "{name} was just added" }],
  },
};
