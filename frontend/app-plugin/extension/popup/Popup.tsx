import { useEffect, useState } from "react";
import { type ExtensionState, type Send, stateOf } from "../messages";
import { Login } from "./Login";
import { Preferences } from "./Preferences";

export function Popup({ send }: { send: Send }) {
  const [state, setState] = useState<ExtensionState | null>(null);

  useEffect(() => {
    void send({ type: "state" }).then((reply) => setState(stateOf(reply)));
  }, [send]);

  return (
    <main className="popup" aria-busy={state === null}>
      <h1 className="popup-title">Alpha Impact</h1>
      {state?.signedIn === false && <Login send={send} onState={setState} />}
      {state?.signedIn === true && <Preferences state={state} send={send} onState={setState} />}
    </main>
  );
}
