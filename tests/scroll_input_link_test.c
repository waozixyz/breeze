#include "platform/scroll_input.h"
#include "session.h"

int main(void)
{
    Rectangle bounds = {20.0f, 10.0f, 80.0f, 40.0f};
    Vector2 mouse = {95.0f, 20.0f};
    Session session = SessionOpen();
    if(!SessionValid(session))
        return 4;
    BeginScrollFrame(session, mouse, true, true, false, -1.0f);
    ScrollInput input = ScrollObservationFor(7, bounds);
    if(!input.enabled || !input.pointer_allowed || input.wheel != -1.0f)
        return 1;

    ScrollFrame frame = {0};
    frame.start_drag = true;
    frame.consume_wheel = true;
    frame.grab = 3.0f;
    CommitScroll(7, frame);
    input = ScrollObservationFor(7, bounds);
    if(!input.owns_drag || input.wheel != 0.0f || input.grab != 3.0f)
        return 2;
    input = ScrollObservationFor(8, bounds);
    if(!input.owner_captured || input.pointer_allowed)
        return 3;
    return SessionClose(session) ? 0 : 5;
}
