// The package and the native fallback share the editor's confirmations.
import { Session } from "kryon/session";
import { ButtonTone, ButtonEmphasis } from "kryon/control_props";
import { ActionModalAction, ActionModalResult } from "kryon/modal";
import { ActionModal } from "kryon/tsx/action_modal";

export interface HabitEditorDialogProps {
    session: Session;
    deleting: boolean;
    title: string;
    message: string;
    keep_editing: string;
    save: string;
    discard: string;
    cancel: string;
    delete_label: string;
}

export function HabitEditorDialog(props: HabitEditorDialogProps): ActionModalResult {
    if (props.deleting) {
        const actions: [ActionModalAction, ActionModalAction] = [
            {
                label: props.cancel,
                tone: ButtonTone.ButtonToneNeutral,
                emphasis: ButtonEmphasis.ButtonEmphasisSoft
            },
            {
                label: props.delete_label,
                tone: ButtonTone.ButtonToneDanger,
                emphasis: ButtonEmphasis.ButtonEmphasisFilled
            }
        ];
        return (
            <ActionModal
                session={props.session}
                actions={actions[:]}
                props={{ title: props.title, message: props.message }}
            />
        );
    }

    const actions: [ActionModalAction, ActionModalAction, ActionModalAction] = [
        {
            label: props.keep_editing,
            tone: ButtonTone.ButtonToneNeutral,
            emphasis: ButtonEmphasis.ButtonEmphasisSoft
        },
        {
            label: props.save,
            tone: ButtonTone.ButtonToneAccent,
            emphasis: ButtonEmphasis.ButtonEmphasisFilled
        },
        {
            label: props.discard,
            tone: ButtonTone.ButtonToneDanger,
            emphasis: ButtonEmphasis.ButtonEmphasisSoft
        }
    ];
    return (
        <ActionModal
            session={props.session}
            actions={actions[:]}
            props={{ title: props.title, message: props.message }}
        />
    );
}
