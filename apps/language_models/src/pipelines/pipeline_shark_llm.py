class LanguageModel:
    def __init__(
        self,
        shark_llm_model,
        tokenizer,
    ):
        self.shark_llm_model = shark_llm_model
        self.tokenizer = tokenizer


    def generate_tokens(self, model, tokenizer, ):
        # For Vic 
        prompt_history = "A chat between a curious user and an artificial intelligence assistant. The assistant gives helpful, detailed, and polite answers to the user's questions.\n"
        prologue_prompt = "ASSISTANT:\n"
        past_key_values = None
        while True:
            print("\n\n")
            user_prompt = input("User: ")
            prompt_history = (
                prompt_history + "USER:\n" + user_prompt + prologue_prompt
            )
            prompt = prompt_history.strip()
            max_response_len = 1000
            input_ids = tokenizer(prompt).input_ids
            tokens = input_ids
            print("Robot:", end=" ")
            new_sentence = []
            past_key_values = None  # for iteration 0
            for iteration in range(max_response_len):
                original_input_ids = input_ids

                params = {
                    "past_key_values": past_key_values,
                    "input_ids": input_ids,
                    "iteration": iteration,
                }
                generated_token_op = generate_new_token(
                    model, tokenizer, params
                )
                # extract result from generate new token
                new_token = generated_token_op["new_token"]
                detok = generated_token_op["detok"]
                past_key_values = generated_token_op["past_key_values"]

                if new_token == 2:
                    break
                new_sentence += [new_token]
                tokens.append(new_token)
                if detok == "<0x0A>":
                    print("\n", end="", flush=True)
                else:
                    print(f"{detok}", end=" ", flush=True)
                original_input_ids.append(new_token)
                input_ids = [new_token]

            for i in range(len(tokens)):
                if type(tokens[i]) != int:
                    tokens[i] = int(tokens[i][0])
            new_sentence_str = tokenizer.decode(new_sentence)
            print(
                "\n-----\nRobot: Here's the complete formatted reply:\n",
                new_sentence_str,
            )
            prompt_history += f"\n{new_sentence_str}\n"


    def from_pretrained(model, model_inputs, model_name, device, precision):
        from shark.shark_inference import SharkInference

        # device = "cuda"  # "cpu"
        # TODO: vmfb and mlir name should include precision and device
        vmfb_path = (
            Path(model_name + f"_{device}.vmfb")
            if model_vmfb_name is None
            else Path(model_vmfb_name)
        )
        shark_module = get_vmfb_from_path(
            vmfb_path, device, mlir_dialect="tm_tensor"
        )
        if shark_module is not None:
            return shark_module

        mlir_path = Path(model_name + ".mlir")
        print(
            f"[DEBUG] mlir path {mlir_path} {'exists' if mlir_path.exists() else 'does not exist'}"
        )
        if mlir_path.exists():
            with open(mlir_path, "rb") as f:
                bytecode = f.read()
        else:
            ts_graph = get_torch_mlir_module_bytecode(model, model_inputs)
            module = torch_mlir.compile(
                ts_graph,
                [*model_inputs],
                torch_mlir.OutputType.LINALG_ON_TENSORS,
                use_tracing=False,
                verbose=False,
            )
            bytecode_stream = BytesIO()
            module.operation.write_bytecode(bytecode_stream)
            bytecode = bytecode_stream.getvalue()
        f_ = open(model_name + ".mlir", "wb")
        f_.write(bytecode)
        print("Saved mlir")
        f_.close()

        shark_module = SharkInference(
            mlir_module=bytecode, device=device, mlir_dialect="tm_tensor"
        )
        shark_module.compile()

        path = shark_module.save_module(
            vmfb_path.parent.absolute(), vmfb_path.stem
        )
        print("Saved vmfb at ", str(path))

        return shark_module



